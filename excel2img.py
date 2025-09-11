#!/usr/bin/env python3
import datetime
import time

import uno
import os
import sys
import argparse
from com.sun.star.beans import PropertyValue
from pdf2image import convert_from_path
from PIL import Image, ImageChops


def connect_to_libreoffice():
    """连接已启动的 LibreOffice 服务"""
    local_ctx = uno.getComponentContext()
    resolver = local_ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_ctx
    )
    ctx = resolver.resolve(
        "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"
    )
    return ctx


def excel_to_pdf_uno(input_path, output_pdf, sheet_name=None):
    """UNO 打开 Excel 并按一页宽一页高导出 PDF，并确保释放文档"""
    ctx = connect_to_libreoffice()
    desktop = ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx
    )

    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)

    input_url = uno.systemPathToFileUrl(os.path.abspath(input_path))
    output_url = uno.systemPathToFileUrl(os.path.abspath(output_pdf))

    doc = None
    try:
        doc = desktop.loadComponentFromURL(input_url, "_blank", 0, ())

        # 如果指定了sheet_name，只处理该sheet
        if sheet_name:
            # 查找指定的sheet
            target_sheet = None
            sheet_index = -1
            for i, sheet in enumerate(doc.Sheets):
                if sheet.Name == sheet_name:
                    target_sheet = sheet
                    sheet_index = i
                    break

            if target_sheet is None:
                raise ValueError(f"找不到名为 '{sheet_name}' 的工作表")

            # 设置页面样式
            page_style_name = target_sheet.PageStyle
            page_style = doc.StyleFamilies.getByName("PageStyles").getByName(page_style_name)
            page_style.setPropertyValue("ScaleToPagesX", 1)
            page_style.setPropertyValue("ScaleToPagesY", 1)
            page_style.LeftMargin = 0
            page_style.RightMargin = 0
            page_style.TopMargin = 0
            page_style.BottomMargin = 0
            page_style.setPropertyValue("HeaderIsOn", False)
            page_style.setPropertyValue("FooterIsOn", False)

            # 激活目标sheet
            controller = doc.getCurrentController()
            controller.setActiveSheet(target_sheet)

            # 隐藏其他所有工作表，只显示目标工作表
            for i, sheet in enumerate(doc.Sheets):
                if i != sheet_index:
                    sheet.setPropertyValue("IsVisible", False)
                else:
                    sheet.setPropertyValue("IsVisible", True)

            # 导出PDF（只包含可见的工作表）
            pdf_props = (PropertyValue("FilterName", 0, "calc_pdf_Export", 0),)
        else:
            # 处理所有sheet，设置一页宽一页高 + 0 边距
            for sheet in doc.Sheets:
                page_style_name = sheet.PageStyle
                page_style = doc.StyleFamilies.getByName("PageStyles").getByName(page_style_name)
                page_style.setPropertyValue("ScaleToPagesX", 1)
                page_style.setPropertyValue("ScaleToPagesY", 1)
                page_style.LeftMargin = 0
                page_style.RightMargin = 0
                page_style.TopMargin = 0
                page_style.BottomMargin = 0
                page_style.setPropertyValue("HeaderIsOn", False)
                page_style.setPropertyValue("FooterIsOn", False)

            # 导出所有sheet的PDF
            pdf_props = (PropertyValue("FilterName", 0, "calc_pdf_Export", 0),)

        doc.storeToURL(output_url, pdf_props)

        # 如果之前隐藏了工作表，现在恢复全部可见性
        if sheet_name:
            for sheet in doc.Sheets:
                sheet.setPropertyValue("IsVisible", True)

    finally:
        # 确保文档被关闭并释放
        if doc:
            try:
                doc.close(True)
            except Exception:
                pass
            try:
                doc.dispose()
            except Exception:
                pass

    if not os.path.exists(output_pdf):
        raise FileNotFoundError(f"PDF 导出失败: {output_pdf}")

    return output_pdf


def crop_blank(img: Image.Image, threshold=240) -> Image.Image:
    """自动裁剪空白边缘"""
    img = img.convert("RGB")
    bg_color = (255, 255, 255)
    bg = Image.new(img.mode, img.size, bg_color)
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def pdf_to_images(pdf_path, out_dir, dpi=200, poppler_path=None):
    """PDF -> PNG 并裁剪空白"""
    os.makedirs(out_dir, exist_ok=True)
    images = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
    saved = []
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    for i, img in enumerate(images, start=1):
        img_cropped = crop_blank(img)
        out_path = os.path.join(out_dir, f"{base}_page{i}.png")
        img_cropped.save(out_path, "PNG")
        saved.append(out_path)
    return saved


def process_file(input_path, dpi=200, out_dir=None, poppler=None, keep_pdf=False, sheet_name=None):
    """完整流程：Excel -> PDF(一页宽) -> PNG"""
    # 创建out_dir 目录，路径为当前目录/tmp/日期
    if out_dir is None:
        from temp_utils import create_excel_temp_dir
        out_dir = create_excel_temp_dir()
    os.makedirs(out_dir, exist_ok=True)

    # 确保输入文件存在
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"文件不存在: {input_path}")
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    pdf_path = os.path.join(out_dir, base_name + ".pdf")

    # 导出 PDF
    excel_to_pdf_uno(input_path, pdf_path, sheet_name)

    # 转 PNG
    imgs = pdf_to_images(pdf_path, out_dir, dpi=dpi, poppler_path=poppler)

    # 根据参数决定是否删除 PDF
    if not keep_pdf:
        try:
            os.remove(pdf_path)
        except Exception:
            pass

    return imgs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="输入 Excel 文件")
    parser.add_argument("--out", default="out", help="输出目录")
    parser.add_argument("--dpi", type=int, default=200, help="图片 DPI")
    parser.add_argument("--poppler", help="Windows 下需要指定 poppler bin 路径")
    parser.add_argument("--keep-pdf", action="store_true", help="是否保留生成的 PDF")
    parser.add_argument("--sheet-name", help="指定 sheet 名称，只处理指定的 sheet")
    args = parser.parse_args()

    input_path = args.input
    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)

    imgs = process_file(
        input_path,
        dpi=args.dpi,
        out_dir=args.out,
        poppler=args.poppler,
        keep_pdf=args.keep_pdf,
        sheet_name=args.sheet_name
    )

    print(f"生成图片: {imgs}")


if __name__ == "__main__":
    main()
