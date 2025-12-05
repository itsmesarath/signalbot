#!/usr/bin/env python3
"""
HFT Signal Generator Backend API Test Suite
Tests all backend endpoints for functionality and data integrity.
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Backend URL from environment
BACKEND_URL = "https://orderflow-ai-1.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.results = []
        
    def log_result(self, test_name: str, success: bool, message: str, response_data: Optional[Dict] = None):
        """Log test result."""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'response_data': response_data
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        if response_data and not success:
            print(f"   Response: {json.dumps(response_data, indent=2)}")
    
    def test_health_endpoint(self):
        """Test GET /api/health endpoint."""
        try:
            response = self.session.get(f"{BACKEND_URL}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    self.log_result("Health Check", True, "Backend is healthy", data)
                    return True
                else:
                    self.log_result("Health Check", False, f"Unhealthy status: {data.get('status')}", data)
            else:
                self.log_result("Health Check", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Health Check", False, f"Connection error: {str(e)}")
        
        return False
    
    def test_settings_endpoint(self):
        """Test GET /api/settings endpoint."""
        try:
            response = self.session.get(f"{BACKEND_URL}/settings", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Check if settings structure is valid
                expected_keys = ['rithmic', 'binance', 'openrouter', 'signal_weights']
                has_structure = any(key in data for key in expected_keys)
                
                if has_structure:
                    self.log_result("Settings Retrieval", True, "Settings retrieved successfully", data)
                    return True
                else:
                    self.log_result("Settings Retrieval", False, "Invalid settings structure", data)
            else:
                self.log_result("Settings Retrieval", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Settings Retrieval", False, f"Error: {str(e)}")
        
        return False
    
    def test_data_source_connect(self):
        """Test POST /api/data-source/connect for simulated data."""
        try:
            url = f"{BACKEND_URL}/data-source/connect?source=simulated&symbol=TEST"
            response = self.session.post(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.log_result("Data Source Connect", True, "Connected to simulated data source", data)
                    return True
                else:
                    self.log_result("Data Source Connect", False, f"Connection failed: {data}", data)
            else:
                self.log_result("Data Source Connect", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Data Source Connect", False, f"Error: {str(e)}")
        
        return False
    
    def test_data_source_status(self, expected_streaming=True):
        """Test GET /api/data-source/status endpoint."""
        try:
            response = self.session.get(f"{BACKEND_URL}/data-source/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                is_streaming = data.get('is_streaming', False)
                
                if is_streaming == expected_streaming:
                    status_msg = "streaming" if expected_streaming else "not streaming"
                    self.log_result("Data Source Status", True, f"Status correct: {status_msg}", data)
                    return True
                else:
                    expected_msg = "streaming" if expected_streaming else "not streaming"
                    actual_msg = "streaming" if is_streaming else "not streaming"
                    self.log_result("Data Source Status", False, f"Expected {expected_msg}, got {actual_msg}", data)
            else:
                self.log_result("Data Source Status", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Data Source Status", False, f"Error: {str(e)}")
        
        return False
    
    def test_current_signal(self):
        """Test GET /api/signals/current endpoint."""
        try:
            response = self.session.get(f"{BACKEND_URL}/signals/current", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if signal has required fields
                if 'signal_type' in data:
                    if data['signal_type'] != 'no_trade' or 'hfss_score' in data:
                        self.log_result("Current Signal", True, "Signal retrieved successfully", data)
                        return True
                    else:
                        self.log_result("Current Signal", True, "No signal generated yet (expected for new connection)", data)
                        return True
                else:
                    self.log_result("Current Signal", False, "Invalid signal structure", data)
            else:
                self.log_result("Current Signal", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Current Signal", False, f"Error: {str(e)}")
        
        return False
    
    def test_metrics_endpoint(self):
        """Test GET /api/metrics endpoint."""
        try:
            response = self.session.get(f"{BACKEND_URL}/metrics", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for expected metric sections
                expected_sections = ['delta', 'absorption', 'iceberg', 'momentum', 'structure']
                has_sections = any(section in data for section in expected_sections)
                
                if has_sections:
                    self.log_result("Metrics Retrieval", True, "Metrics retrieved successfully", data)
                    return True
                else:
                    self.log_result("Metrics Retrieval", False, "Missing expected metric sections", data)
            else:
                self.log_result("Metrics Retrieval", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Metrics Retrieval", False, f"Error: {str(e)}")
        
        return False
    
    def test_signal_history(self):
        """Test GET /api/signals/history endpoint."""
        try:
            response = self.session.get(f"{BACKEND_URL}/signals/history?limit=10", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'signals' in data:
                    signals = data['signals']
                    self.log_result("Signal History", True, f"Retrieved {len(signals)} historical signals", data)
                    return True
                else:
                    self.log_result("Signal History", False, "Invalid response structure", data)
            else:
                self.log_result("Signal History", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Signal History", False, f"Error: {str(e)}")
        
        return False
    
    def test_data_source_disconnect(self):
        """Test POST /api/data-source/disconnect endpoint."""
        try:
            response = self.session.post(f"{BACKEND_URL}/data-source/disconnect", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.log_result("Data Source Disconnect", True, "Disconnected successfully", data)
                    return True
                else:
                    self.log_result("Data Source Disconnect", False, f"Disconnect failed: {data}", data)
            else:
                self.log_result("Data Source Disconnect", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_result("Data Source Disconnect", False, f"Error: {str(e)}")
        
        return False
    
    def wait_for_signal_generation(self, max_wait=30):
        """Wait for signals to be generated after connecting."""
        print(f"⏳ Waiting up to {max_wait}s for signal generation...")
        
        for i in range(max_wait):
            try:
                response = self.session.get(f"{BACKEND_URL}/signals/current", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('signal_type') != 'no_trade' and 'hfss_score' in data:
                        print(f"✅ Signal generated after {i+1}s")
                        return True
                        
            except Exception:
                pass
                
            time.sleep(1)
        
        print(f"⚠️  No signal generated after {max_wait}s (may be normal)")
        return False
    
    def run_full_test_suite(self):
        """Run complete backend test suite."""
        print("🚀 Starting HFT Signal Generator Backend Test Suite")
        print(f"🔗 Testing backend at: {BACKEND_URL}")
        print("=" * 60)
        
        # Test 1: Health check
        if not self.test_health_endpoint():
            print("❌ Backend health check failed - aborting tests")
            return False
        
        # Test 2: Settings
        self.test_settings_endpoint()
        
        # Test 3: Connect to simulated data source
        if self.test_data_source_connect():
            # Test 4: Check connection status (should be streaming)
            time.sleep(2)  # Allow connection to establish
            self.test_data_source_status(expected_streaming=True)
            
            # Wait for some data to be processed
            self.wait_for_signal_generation()
            
            # Test 5: Current signal
            self.test_current_signal()
            
            # Test 6: Metrics
            self.test_metrics_endpoint()
            
            # Test 7: Signal history
            self.test_signal_history()
            
            # Test 8: Disconnect
            self.test_data_source_disconnect()
            
            # Test 9: Verify disconnected
            time.sleep(1)
            self.test_data_source_status(expected_streaming=False)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r['success'])
        total = len(self.results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if total - passed > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.results:
                if not result['success']:
                    print(f"   • {result['test']}: {result['message']}")
        
        return passed == total

def main():
    """Main test execution."""
    tester = BackendTester()
    success = tester.run_full_test_suite()
    
    # Save detailed results
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(tester.results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /app/backend_test_results.json")
    
    if success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed - check results above")
        sys.exit(1)

if __name__ == "__main__":
    main()