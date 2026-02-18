# -*- coding: utf-8 -*-
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEXTTS_DIR = os.path.join(BASE_DIR, "IndexTTS2-SonicVale")
sys.path.insert(0, INDEXTTS_DIR)

print("[TEST] Starting import test...")

try:
    print("[TEST] Importing unified_app...")
    import unified_app
    print("[TEST] OK Import successful")
    
    print("[TEST] Calling build_ui()...")
    app = unified_app.build_ui()
    print("[TEST] OK build_ui() successful")
    
    print("[TEST] Launching on port 7870...")
    app.launch(server_name="127.0.0.1", server_port=7870, inbrowser=False, quiet=False)
    
except Exception as e:
    print(f"[TEST] ERROR: {e}")
    import traceback
    traceback.print_exc()
