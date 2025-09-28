import numpy as np


def letterbox(im, new_shape=(640, 640), color=(114, 114, 114)):
    """
    Resize and pad image to meeting new_shape (like Ultralytics letterbox).
    Returns: new_img, ratio, (pad_w, pad_h)
    """
    shape = im.shape[:2]  # h, w
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)

    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))
    dw = new_shape[1] - new_unpad[0]
    dh = new_shape[0] - new_unpad[1]
    dw /= 2
    dh /= 2

    # resize
    im_resized = np.zeros(
        (new_shape[0], new_shape[1], 3), dtype=im.dtype
    ) + np.array(color, dtype=im.dtype)
    import cv2

    im_small = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, left = int(round(dh)), int(round(dw))
    im_resized[top : top + new_unpad[1], left : left + new_unpad[0]] = im_small
    return im_resized, r, (left, top)


def xywh2xyxy(x):
    """Convert nx4 [x_center, y_center, w, h] -> [x1,y1,x2,y2]"""
    y = x.copy()
    y[:, 0] = x[:, 0] - x[:, 2] / 2
    y[:, 1] = x[:, 1] - x[:, 3] / 2
    y[:, 2] = x[:, 0] + x[:, 2] / 2
    y[:, 3] = x[:, 1] + x[:, 3] / 2
    return y


def compute_iou(box, boxes):
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])

    inter_w = np.maximum(0.0, x2 - x1)
    inter_h = np.maximum(0.0, y2 - y1)
    inter = inter_w * inter_h
    area1 = (box[2] - box[0]) * (box[3] - box[1])
    area2 = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    union = area1 + area2 - inter
    return inter / (union + 1e-6)


def nms(boxes, scores, iou_thres=0.45):
    """Classic NMS for a set of boxes and scores. boxes: (N,4), scores: (N,)"""
    if boxes.shape[0] == 0:
        return []
    idxs = scores.argsort()[::-1]
    keep = []
    while idxs.size:
        i = idxs[0]
        keep.append(i)
        if idxs.size == 1:
            break
        ious = compute_iou(boxes[i], boxes[idxs[1:]])
        idxs = idxs[1:][ious < iou_thres]
    return keep


def process_yolo_output(
    output,
    img_shape=(640, 640),
    orig_shape=None,
    conf_thres=0.25,
    iou_thres=0.45,
    classes=None,
):
    """
    output: outputs[0] from ONNX - expected shape (1, C, N) or (1, 15, 8400)
    img_shape: size used for inference (width,height) or (h,w)
    orig_shape: original image (h,w) to scale boxes back, if provided
    returns: list of detections: {"bbox":[x1,y1,x2,y2], "score":float, "class_id":int}
    """
    out = np.array(output)  # ensure np
    # out expected (1, C, N) -> transpose to (N, C)
    # handle both (1, C, N) and (1, N, C)
    if out.ndim == 3:
        # if shape (1, C, N)
        if out.shape[1] <= out.shape[2]:
            out = out[0].transpose(1, 0)  # (N, C)
        else:
            # sometimes already (1, N, C)
            out = out[0]
    else:
        out = out.squeeze()
        if out.ndim == 2 and out.shape[1] <= 20:
            out = out.transpose(1, 0)

    # Now out is (num_preds, C) where C = 4 + num_classes
    if out.size == 0:
        return []

    boxes_xywh = out[
        :, :4
    ].copy()  # x_center, y_center, w, h (likely in pixels wrt padded image)
    scores_all = out[
        :, 4:
    ]  # class scores (no separate obj_conf in this export)

    class_ids = np.argmax(scores_all, axis=1)
    class_scores = scores_all[np.arange(scores_all.shape[0]), class_ids]

    # Filter by conf threshold
    mask = class_scores > conf_thres
    if not mask.any():
        return []

    boxes_xywh = boxes_xywh[mask]
    class_scores = class_scores[mask]
    class_ids = class_ids[mask]

    # Convert to xyxy
    boxes_xyxy = xywh2xyxy(boxes_xywh)

    # If coords are relative (0..1) or in pixels? We try to infer:
    # If max coordinate <= 1 -> probably normalized -> scale to img_shape
    # Else assume coordinates are in pixels for inference image size (e.g. 640)
    max_coord = boxes_xyxy.max()
    inference_size = (
        img_shape[0] if isinstance(img_shape, (tuple, list)) else img_shape
    )
    if max_coord <= 1.0:
        boxes_xyxy = boxes_xyxy * inference_size

    # Now perform per-class NMS and collect final detections
    final = []
    unique_classes = np.unique(class_ids)
    for c in unique_classes:
        idxs = np.where(class_ids == c)[0]
        b = boxes_xyxy[idxs]
        s = class_scores[idxs]
        keep = nms(b, s, iou_thres=iou_thres)
        for k in keep:
            det = {
                "bbox": b[k].tolist(),
                "score": float(s[k]),
                "class_id": int(c),
            }
            final.append(det)

    # Optionally re-scale from padded inference image back to original image shape should be done outside
    # (since letterbox may have been used we will correct that in main code).
    return final
