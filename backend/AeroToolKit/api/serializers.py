import base64
import uuid
import time
import io
import os
import numpy as np
import onnxruntime as ort
from rest_framework import serializers
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from instruments.models import Instrument
from django.core.files.base import ContentFile
from instruments.models import Instrument
from .yolo_utils import letterbox, process_yolo_output


YOLO_CLASSES = [
    '1_screwdriver_minus',  # Отвертка «-»
    '2_screwdriver_plus',  # Отвертка «+»
    '3_screwdriver_torq',  # Отвертка на смещенный крест
    '4_brace',  # Коловорот
    '5_locking_pliers',  # Пассатижи контровочные
    '6_pliers',  # Пассатижи
    '7_adjustable_pliers',  # Шэрница
    '8_adjustable_wrench',  # Разводной ключ
    '9_can_opener',  # Открывашка для банок с маслом
    '10_open_end_wrench',  # Ключ рожковый накидной ¾
    '11_sidecutter',  # Бокорезы
]
#  model_path = os.path.join(
#     #             os.path.dirname(__file__), 'yolo_models', 'yolo_model.onnx'
#     #         )
# YOLO_MODEL_PATH = "D:/Dev/hackathon/Aeroflot_Hackathon/backend/AeroToolKit/api/yolo_models/yolo_model.onnx"

YOLO_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), 'yolo_models', 'yolo_model.onnx'
)

ort_session = ort.InferenceSession(
    YOLO_MODEL_PATH, providers=["CPUExecutionProvider"]
)


class InstrumentSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(
        source='employee.username', read_only=True
    )
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Instrument
        fields = [
            'id',
            'text',
            'pub_date',
            'employee',
            'employee_username',
            'image',
            'image_url',
        ]
        read_only_fields = ['employee', 'pub_date']

    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class InstrumentCreateSerializer(serializers.ModelSerializer):
    full_base64_string = serializers.CharField(write_only=True, required=True)
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Instrument
        fields = [
            'id',
            'text',
            'pub_date',
            'employee',
            'image',
            'full_base64_string',
        ]
        read_only_fields = ['employee', 'pub_date', 'image']

    def validate(self, attrs):
        errors = {}
        if not attrs.get('text', '').strip():
            errors['text'] = 'Текст обязателен'
        full_base64_string = attrs.get('full_base64_string', '')
        if not full_base64_string:
            errors['full_base64_string'] = (
                'Изображение в формате base64 обязательно'
            )
        elif not full_base64_string.startswith('data:image/'):
            errors['full_base64_string'] = 'Неверный формат base64'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        full_base64_string = validated_data.pop("full_base64_string")
        base64_data = full_base64_string.split(",", 1)[1]

        try:
            image_data = base64.b64decode(base64_data)
        except Exception as e:
            raise serializers.ValidationError(
                {"full_base64_string": f"Ошибка base64: {str(e)}"}
            )

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["employee"] = request.user
        else:
            raise serializers.ValidationError(
                {"employee": "Пользователь не аутентифицирован"}
            )

        # Run YOLO on image_data
        yolo_results, processed_image_bytes = self.run_yolo_inference(
            image_data
        )

        # Add YOLO results to text
        original_text = validated_data.get("text", "")
        validated_data["text"] = self.add_yolo_results_to_text(
            original_text, yolo_results
        )

        # Create filename and save
        image_format = full_base64_string.split(";")[0].split("/")[1]
        filename = f"instrument_{uuid.uuid4().hex[:8]}.{image_format}"

        instrument = Instrument(**validated_data)
        instrument.image.save(filename, ContentFile(processed_image_bytes))

        return instrument

    def run_yolo_inference(
        self, image_data, imgsz=640, conf_thres=0.7, iou_thres=0.7
    ):
        start = time.time()

        # Load image and convert to numpy
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        orig_w, orig_h = image.size
        img_np = np.array(image)  # H,W,3 RGB

        # Letterbox (same preprocessing as during training/inference in Ultralytics)
        img_pad, ratio, (pad_w, pad_h) = letterbox(
            img_np, new_shape=(imgsz, imgsz)
        )
        # Prepare input: HWC -> CHW, BGR? Ultralytics expects RGB after letterbox, but common flow:
        # ONNX exported by ultralytics expects (1,3,640,640) with channels RGB normalized to [0,1]
        img_input = img_pad[:, :, ::-1].transpose(
            2, 0, 1
        )  # RGB->BGR-> then we convert to float; if your ONNX expects RGB change this line
        # Note: if results look swapped colors, change to img_pad.transpose(2,0,1) (RGB)
        img_input = (
            np.expand_dims(img_input, axis=0).astype(np.float32) / 255.0
        )

        # Run ONNX
        ort_inputs = {ort_session.get_inputs()[0].name: img_input}
        outputs = ort_session.run(None, ort_inputs)
        # outputs[0] expected shape (1, C, N) e.g. (1,15,8400)
        processed = process_yolo_output(
            outputs[0],
            img_shape=imgsz,
            orig_shape=(orig_h, orig_w),
            conf_thres=conf_thres,
            iou_thres=iou_thres,
        )

        # processed: list of {"bbox":[x1,y1,x2,y2] (in padded image coords), "score":float, "class_id":int}
        # Need to convert boxes from padded(640x640) -> original image coordinates:
        detections = []
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        for det in processed:
            x1, y1, x2, y2 = det["bbox"]
            # remove padding and scale by ratio back to original
            # pad_w,pad_h were applied to left/top respectively (in pixels)
            # when letterbox put image into padded canvas: left = pad_w, top = pad_h
            # So to revert: (coord - pad) / ratio
            x1 = (x1 - pad_w) / ratio
            x2 = (x2 - pad_w) / ratio
            y1 = (y1 - pad_h) / ratio
            y2 = (y2 - pad_h) / ratio

            # Clip
            x1 = max(0, min(orig_w, int(round(x1))))
            x2 = max(0, min(orig_w, int(round(x2))))
            y1 = max(0, min(orig_h, int(round(y1))))
            y2 = max(0, min(orig_h, int(round(y2))))

            class_id = det["class_id"]
            cls_name = (
                YOLO_CLASSES[class_id]
                if class_id < len(YOLO_CLASSES)
                else str(class_id)
            )
            score = float(det["score"])

            detections.append({"class": cls_name, "confidence": score})

            # Draw bbox and label on original image
            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
            label = f"{cls_name} {score:.2f}"
            text_pos = (x1, max(0, y1 - 12))
            draw.text(text_pos, label, fill="red", font=font)

        processing_time = round(time.time() - start, 2)
        result_dict = {
            "detections": detections,
            "processing_time": processing_time,
            "status": "processed" if len(detections) else "no_detections",
        }

        # Save annotated image bytes (JPEG)
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        processed_image_bytes = buf.getvalue()

        return result_dict, processed_image_bytes

    def add_yolo_results_to_text(self, original_text, yolo_results):
        detections = yolo_results.get("detections", [])
        if not detections:
            yolo_section = "YOLO анализ: инструменты не обнаружены"
        else:
            detected_items = [
                f"{i+1}. {det['class']} (Уровень уверенности: {det['confidence']:.2f})"
                for i, det in enumerate(detections)
            ]
            yolo_section = (
                f"YOLO анализ: обнаружено {len(detections)} объектов\n"
                + "\n".join(detected_items)
            )
        return (
            f"{original_text}\n\n{yolo_section}"
            if original_text.strip()
            else yolo_section
        )
