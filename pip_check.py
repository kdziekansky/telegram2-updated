# pip_check.py
import pkg_resources
import sys

for package in pkg_resources.working_set:
    print(f"{package.project_name}=={package.version}")

print("\n--- Supabase details ---")
try:
    import supabase
    print(f"Supabase path: {supabase.__file__}")
    print(f"Supabase version: {supabase.__version__}")
    
    # Sprawdźmy, czy jest funkcja create_client
    from supabase import create_client
    print(f"create_client exists: {create_client.__name__}")
    
    # Sprawdźmy, czy jest klasa Client
    try:
        from supabase._client import Client
        print(f"Client exists in supabase._client")
    except ImportError:
        print("Client not found in supabase._client")
        
    try:
        from supabase.client import Client
        print(f"Client exists in supabase.client")
    except ImportError:
        print("Client not found in supabase.client")
    
except ImportError as e:
    print(f"Error importing supabase: {e}")