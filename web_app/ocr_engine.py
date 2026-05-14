"""使用 macOS 原生 Vision 框架做 OCR，识别中文截图文字。"""
from __future__ import annotations

import io
from pathlib import Path

from Foundation import NSBundle
from PIL import Image

# 确保中文语言资源可用
Vision = NSBundle.bundleWithIdentifier_("com.apple.Vision")


def ocr_image(image_input: str | Path | bytes) -> str:
    """
    对图片进行 OCR 文字识别。

    Args:
        image_input: 图片文件路径(str/Path) 或 PNG bytes

    Returns:
        识别出的文本字符串
    """
    import Quartz
    from Quartz import CIImage
    from Vision import (
        VNRecognizeTextRequest,
        VNRecognizeTextRequestRevision3,
        VNRequestTextRecognitionLevelAccurate,
        VNImageRequestHandler,
    )

    # 加载图片为 CIImage
    if isinstance(image_input, (str, Path)):
        image_url = Quartz.CFURLCreateFromFileSystemRepresentation(
            None, str(image_input).encode("utf-8"), len(str(image_input).encode("utf-8")), False
        )
        ci_image = CIImage.imageWithContentsOfURL_(image_url)
    elif isinstance(image_input, bytes):
        pil_image = Image.open(io.BytesIO(image_input))
        # 转换为 PNG bytes 再创建 CIImage
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        data = buf.getvalue()
        ci_image = CIImage.imageWithData_(data)
    else:
        raise ValueError(f"不支持的输入类型: {type(image_input)}")

    if ci_image is None:
        return ""

    # 创建 OCR 请求
    request = VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_(["zh-Hans", "zh-Hant", "en"])
    request.setUsesLanguageCorrection_(True)
    request.setRevision_(VNRecognizeTextRequestRevision3)

    # 执行识别
    handler = VNImageRequestHandler.alloc().initWithCIImage_options_(ci_image, None)
    success = handler.performRequests_error_([request], None)

    if not success:
        return ""

    # 提取结果
    results = request.results()
    if not results:
        return ""

    lines = []
    for observation in results:
        text = observation.topCandidates_(1)
        if text and len(text) > 0:
            lines.append(text[0].string())

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = ocr_image(sys.argv[1])
        print(result)
    else:
        print("Usage: python ocr_engine.py <image_path>")
