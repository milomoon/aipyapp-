import time
import wx
import wx.adv
import threading
import qrcode
import io
from PIL import Image

from .. import T
from ..aipy.trustoken import TrustTokenAPI

class TrustTokenAuthDialog(wx.Dialog):
    """A dialog for TrustToken authentication with QR code display."""
    
    def __init__(self, parent=None, coordinator_url=None, poll_interval=5):
        """
        Initialize the authentication dialog.
        
        Args:
            parent: Parent window
            coordinator_url (str, optional): The coordinator server URL
            poll_interval (int, optional): Polling interval in seconds
        """
        super().__init__(parent, title=T("TrustToken Authentication"), 
                        size=(400, 500), 
                        style=wx.DEFAULT_DIALOG_STYLE )
        
        self.api = TrustTokenAPI(coordinator_url)
        self.poll_interval = poll_interval
        self.request_id = None
        self.polling_thread = None
        self.stop_polling = False
        self.start_time = None
        self.polling_timeout = 310  # 5 minutes and 10 seconds
        
        self._init_ui()
        self.Centre()
        
    def _init_ui(self):
        """Initialize the user interface."""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
       # Status text
        self.status_text = wx.StaticText(self, label='')
        main_sizer.Add(self.status_text, 0, wx.TOP | wx.ALIGN_CENTER, 5)

        # QR code display
        self.qr_bitmap = wx.StaticBitmap(self, size=(300, 300))
        main_sizer.Add(self.qr_bitmap, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        self.other_text = wx.adv.HyperlinkCtrl(self, label='扫码绑定AiPy大脑，您也可以配置其它大模型大脑', url='https://d.aipy.app/d/77')
        main_sizer.Add(self.other_text, 0, wx.TOP | wx.ALIGN_CENTER, 5)

        # Progress bar
        self.progress_bar = wx.Gauge(self, range=100)
        main_sizer.Add(self.progress_bar, 0, wx.ALL | wx.EXPAND, 5)
        
        # Time remaining text
        self.time_text = wx.StaticText(self, label='')
        self.time_text.Hide()
        main_sizer.Add(self.time_text, 0, wx.ALL | wx.ALIGN_CENTER, 5)
        
        # Buttons
        self.cancel_button = wx.Button(self, wx.ID_CANCEL, T("Cancel"))
        main_sizer.Add(self.cancel_button, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
        
        # Bind events
        self.Bind(wx.EVT_BUTTON, self._on_cancel, self.cancel_button)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        
    def _update_progress(self):
        """Update the progress bar and time remaining."""
        if not self.start_time:
            return
            
        elapsed = time.time() - self.start_time
        if elapsed >= self.polling_timeout:
            progress = 100
            time_remaining = 0
        else:
            progress = int((elapsed / self.polling_timeout) * 100)
            time_remaining = int(self.polling_timeout - elapsed)
            
        wx.CallAfter(self.progress_bar.SetValue, progress)
        wx.CallAfter(self.time_text.SetLabel, T("Time remaining: {} seconds", time_remaining))
        
    def _poll_status(self, save_func):
        """Poll the binding status in a separate thread."""
        self.start_time = time.time()
        self.time_text.Show()
        while not self.stop_polling and time.time() - self.start_time < self.polling_timeout:
            self._update_progress()
            
            data = self.api.check_status(self.request_id)
            if not data:
                time.sleep(self.poll_interval)
                continue
                
            status = data.get('status')
            wx.CallAfter(self._update_status, T("Current status: {}...", T(status)))
            
            if status == 'approved':
                if save_func:
                    save_func(data['secret_token'])
                wx.CallAfter(self.EndModal, wx.ID_OK)
                return True
            elif status == 'expired':
                wx.CallAfter(self._update_status, T("\nBinding request expired."))
                wx.CallAfter(self.EndModal, wx.ID_CANCEL)
                return False
            elif status == 'pending':
                pass
            else:
                wx.CallAfter(self._update_status, T("\nUnknown status received: {}", status))
                wx.CallAfter(self.EndModal, wx.ID_CANCEL)
                return False
                
            time.sleep(self.poll_interval)
            
        if not self.stop_polling:
            wx.CallAfter(self._update_status, T("\nPolling timed out."))
            wx.CallAfter(self.EndModal, wx.ID_CANCEL)
        return False
        
    def _on_cancel(self, event):
        """Handle cancel button click."""
        self.stop_polling = True
        if self.polling_thread:
            self.polling_thread.join()
        self.EndModal(wx.ID_CANCEL)
        
    def _on_close(self, event):
        """Handle dialog close."""
        self.stop_polling = True
        if self.polling_thread:
            self.polling_thread.join()
        event.Skip()
        
    def _update_qr_code(self, url):
        """Update the QR code display with the given URL."""
        try:
            qr = qrcode.QRCode(
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                border=1
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Convert QR code to wx.Bitmap
            img = qr.make_image(fill_color="black", back_color="white")
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            wx_img = wx.Image(io.BytesIO(img_byte_arr))
            wx_img = wx_img.Scale(300, 300, wx.IMAGE_QUALITY_HIGH)
            self.qr_bitmap.SetBitmap(wx.Bitmap(wx_img))
            self.Layout()
        except Exception as e:
            wx.MessageBox(T("(Could not display QR code: {})\n", e), T("Error"), wx.OK | wx.ICON_ERROR)
            
    def _update_status(self, status):
        """Update the status text."""
        self.status_text.SetLabel(status)
        self.Layout()
        
    def fetch_token(self, save_func):
        """Start the token fetching process.
        
        Args:
            save_func (callable): Function to save the token when approved.
            
        Returns:
            bool: True if token was successfully fetched and saved, False otherwise.
        """
        self._update_status(T("Request binding"))
        data = self.api.request_binding()
        if not data:
            wx.MessageBox(T("\nFailed to initiate binding request.", None), T("Error"), wx.OK | wx.ICON_ERROR)
            return False
            
        approval_url = data['approval_url']
        self.request_id = data['request_id']
        expires_in = data['expires_in']
        self.polling_timeout = expires_in
        self._update_status(T("Current status: {}...", T("Waiting for approval")))
        self._update_qr_code(approval_url)
        
        # Start polling in a separate thread
        self.polling_thread = threading.Thread(
            target=self._poll_status, args=(save_func,))
        self.polling_thread.daemon = True
        self.polling_thread.start()
        
        # Show the dialog
        result = self.ShowModal()
        return result == wx.ID_OK

if __name__ == "__main__":
    # Test the TrustTokenAuthDialog
    app = wx.App()
    
    def save_token(token):
        print(f"Token received: {token}")
        # Here you would typically save the token to your configuration
        # For example:
        # config_manager.save_tt_config(token)
    
    # Create and show the dialog
    url = os.getenv('COORDINATOR_URL', 'https://api.trustoken.cn/api')
    dialog = TrustTokenAuthDialog(coordinator_url=url)
    if dialog.fetch_token(save_token):
        print("Authentication successful!")
    else:
        print("Authentication failed or was cancelled.")
    
    app.MainLoop() 