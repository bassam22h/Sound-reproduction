import os
import tempfile

async def create_temp_file(content, suffix='.tmp'):
    """إنشاء ملف مؤقت وإرجاع مساره"""
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(content)
            return temp_file.name
    except Exception as e:
        raise Exception(f"Failed to create temp file: {str(e)}")

async def delete_temp_file(file_path):
    """حذف ملف مؤقت"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        raise Exception(f"Failed to delete temp file: {str(e)}")
