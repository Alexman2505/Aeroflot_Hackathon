import onnxruntime as ort
import os


def inspect_model():
    # Текущая директория где лежит этот скрипт
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'yolo_model.onnx')

    print(f"Looking for model at: {model_path}")
    print(f"Model exists: {os.path.exists(model_path)}")

    if not os.path.exists(model_path):
        print("Model not found! Check the path.")
        return

    session = ort.InferenceSession(model_path)
    model_metadata = session.get_modelmeta()
    print("Model metadata:", model_metadata.custom_metadata_map)

    # Проверяем входы и выходы
    for i, input in enumerate(session.get_inputs()):
        print(
            f"Input {i}: {input.name}, shape: {input.shape}, type: {input.type}"
        )

    for i, output in enumerate(session.get_outputs()):
        print(
            f"Output {i}: {output.name}, shape: {output.shape}, type: {output.type}"
        )


if __name__ == "__main__":
    inspect_model()
