import sys
import os
from fastapi import UploadFile
import asyncio
from app.api.endpoints.duplicate_phones import process_excel
from unittest.mock import MagicMock

async def run_test():
    temp_path = os.path.join('C:\\Users\\User\\AppData\\Local\\Temp\\intranet_excel', 'test_file.xlsx')
    with open(temp_path, 'rb') as f:
        content = f.read()
        
    uf = UploadFile(filename='test_file.xlsx')
    uf.read = lambda: asyncio.sleep(0, result=content) # mock read
    async def mock_read(): return content
    uf.read = mock_read
    
    # call process_excel
    bg = MagicMock()
    res = await process_excel(background_tasks=bg, file=uf)
    import json
    print(res.body.decode('utf-8'))

asyncio.run(run_test())
