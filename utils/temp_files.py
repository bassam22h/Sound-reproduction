import tempfile
import os

def create_temp_file(content, suffix='.tmp'):
    """إنشاء ملف مؤقت وإرجاع مساره"""
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_file.write(content)
            return tmp_file.name
    except Exception as e:
        raise Exception(f"فشل إنشاء الملف المؤقت: {str(e)}")

def delete_temp_file(file_path):
    """حذف ملف مؤقت"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        raise Exception(f"فشل حذف الملف المؤقت: {str(e)}")
