import os
import sys
import time
import requests
import qrcode

from .. import T

POLL_INTERVAL = 5 # 轮询间隔（秒）

class TrustTokenAPI:
    """Handles all HTTP operations for TrustToken binding and authentication."""
    
    def __init__(self, coordinator_url):
        """
        Initialize the TrustToken API handler.
        
        Args:
            coordinator_url (str): The coordinator server URL.
        """
        assert(coordinator_url)
        self.coordinator_url = coordinator_url

    def request_binding(self):
        """Request binding from the coordinator server.
        
        Returns:
            dict: Response data containing approval_url, request_id, and expires_in if successful
            None: If the request failed
        """
        url = f"{self.coordinator_url}/request_bind"
        try:
            response = requests.post(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(T("Error connecting to coordinator or during request: {}").format(e))
            return None
        except Exception as e:
            print(T("An unexpected error occurred during request: {}").format(e))
            return None

    def check_status(self, request_id):
        """Check the binding status from the coordinator server.
        
        Args:
            request_id (str): The request ID to check status for.
            
        Returns:
            dict: Response data containing status and secret_token if approved
            None: If the request failed
        """
        url = f"{self.coordinator_url}/check_status"
        params = {'request_id': request_id}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(T("Error connecting to coordinator during polling: {}").format(e))
            return None
        except Exception as e:
            print(T("An unexpected error occurred during polling: {}").format(e))
            return None

class TrustToken:
    """A class to handle TrustToken binding and authentication processes."""
    
    def __init__(self, coordinator_url=None, poll_interval=5):
        """
        Initialize the TrustToken handler.
        
        Args:
            coordinator_url (str, optional): The coordinator server URL. Defaults to None.
            poll_interval (int, optional): Polling interval in seconds. Defaults to 5.
        """
        self.api = TrustTokenAPI(coordinator_url)
        self.poll_interval = poll_interval or POLL_INTERVAL

    def request_binding(self):
        """Request binding from the coordinator server.
        
        Returns:
            str: The request ID if successful, None otherwise.
        """
        data = self.api.request_binding()
        if not data:
            return None

        approval_url = data['approval_url']
        request_id = data['request_id']
        expires_in = data['expires_in']

        print(T("Binding request sent successfully.\nRequest ID: {}\n\n>>> Please open this URL in your browser on an authenticated device to approve:\n>>> {}\n\n(This link expires in {} seconds)").format(request_id, approval_url, expires_in))
        print(T("Or scan the QR code below:"))

        try:
            qr = qrcode.QRCode(
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                border=1
            )
            qr.add_data(approval_url)
            qr.make(fit=True)
            is_windows = sys.platform.startswith("win")
            qr.print_ascii(tty=not is_windows)
            print(T("We recommend you scan the QR code to bind the AiPy brain, you can also configure a third-party large model brain, details refer to: https://d.aipy.app/d/77"))
        except Exception as e:
            print(T("(Could not display QR code: {})\n").format(e))

        return request_id

    def poll_status(self, request_id, save_func=None):
        """Poll the binding status from the coordinator server.
        
        Args:
            request_id (str): The request ID to check status for.
            save_func (callable, optional): Function to save the token when approved.
            
        Returns:
            bool: True if binding was successful, False otherwise.
        """
        start_time = time.time()
        polling_timeout = 310

        print(T("Waiting for approval"), end='', flush=True)
        try:
            while time.time() - start_time < polling_timeout:
                data = self.api.check_status(request_id)
                if not data:
                    time.sleep(self.poll_interval)
                    continue

                status = data.get('status')
                if status == 'pending':
                    print('.', end='', flush=True)
                    time.sleep(self.poll_interval)
                    continue

                print()
                print(T("Current status: {}...").format(status))

                if status == 'approved':
                    if save_func:
                        save_func(data['secret_token'])
                    return True
                elif status == 'expired':
                    print(T("\nBinding request expired."))
                    return False
                else:
                    print(T("\nUnknown status received: {}").format(status))
                    return False

                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print(T("\nPolling cancelled by user."))
            return False

        print(T("\nPolling timed out."))
        return False

    def fetch_token(self, save_func):
        """Fetch a token from the coordinator server.
        
        Args:
            save_func (callable): Function to save the token when approved.
            
        Returns:
            bool: True if token was successfully fetched and saved, False otherwise.
        """
        print(T("The current environment lacks the required configuration file. Starting the configuration initialization process to bind with the Trustoken account..."))
        req_id = self.request_binding()
        if req_id:
            if self.poll_status(req_id, save_func):
                print(T("\nBinding process completed successfully."))
                return True
            else:
                print(T("\nBinding process failed or was not completed."))
                return False
        else:
            print(T("\nFailed to initiate binding request."))
            return False

if __name__ == "__main__":
    url = os.getenv('COORDINATOR_URL', 'https://api.trustoken.cn/api')
    tt = TrustToken(coordinator_url=url)
    tt.fetch_token(lambda token: print(f"Token: {token}"))