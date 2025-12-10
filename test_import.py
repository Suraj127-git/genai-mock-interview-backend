#!/usr/bin/env python3
"""Test script to verify the import fix."""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    # Test the main import that was failing
    from core.sentry import capture_exception
    print("✓ Successfully imported capture_exception from core.sentry")
    
    # Test all the functions that should now be available
    from core.logging import (
        capture_exception as logging_capture_exception,
        capture_message,
        add_breadcrumb,
        set_user_context,
        set_context,
        start_span
    )
    print("✓ Successfully imported all Sentry-compatible functions from core.logging")
    
    # Test that the functions work
    try:
        # Test capture_exception
        test_error = ValueError("Test error")
        logging_capture_exception(test_error, tags={"test": "true"})
        print("✓ capture_exception function works")
        
        # Test capture_message
        capture_message("Test message", level="info")
        print("✓ capture_message function works")
        
        # Test add_breadcrumb
        add_breadcrumb("Test breadcrumb", category="test")
        print("✓ add_breadcrumb function works")
        
        # Test set_user_context
        set_user_context({"id": "test_user", "email": "test@example.com"})
        print("✓ set_user_context function works")
        
        # Test set_context
        set_context("test_context", {"key": "value"})
        print("✓ set_context function works")
        
        # Test start_span
        with start_span("test_operation", "Test operation"):
            pass
        print("✓ start_span function works")
        
        print("\n🎉 All imports and functions are working correctly!")
        
    except Exception as e:
        print(f"✗ Error testing functions: {e}")
        sys.exit(1)
        
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Unexpected error: {e}")
    sys.exit(1)