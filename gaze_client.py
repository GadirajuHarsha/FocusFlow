import socket
import xml.etree.ElementTree as ET

# Helper to read a 7-bit encoded integer (for string length) from the socket
def read_7bit_encoded_int(sock):
    num = 0
    shift = 0
    while True:
        byte_val = sock.recv(1)
        if not byte_val:
            raise ConnectionAbortedError("Socket closed while reading string length")
        byte_val = byte_val[0]
        
        num |= (byte_val & 0x7F) << shift
        shift += 7
        if (byte_val & 0x80) == 0:
            # MSB is 0, so this is the last byte for the length
            break
    return num

# Helper to read a string that is prefixed with its 7-bit encoded length
def read_length_prefixed_string(sock):
    length = read_7bit_encoded_int(sock)
    if length == 0:
        return ""
    if length < 0:
        # Should not happen with GazeFlow's positive lengths
        raise ValueError("Received negative string length, protocol error.")
        
    # Read the string data itself
    data_bytes = b''
    bytes_to_read = length
    while bytes_to_read > 0:
        # Read in chunks
        chunk = sock.recv(min(bytes_to_read, 4096)) 
        if not chunk:
            raise ConnectionAbortedError("Socket closed while reading string data")
        data_bytes += chunk
        bytes_to_read -= len(chunk)
        
    return data_bytes.decode('utf-8')

# Helper to get bytes for a 7-bit encoded integer
def get_7bit_encoded_int_bytes(num):
    if num < 0:
        raise ValueError("Length cannot be negative.")
    bytes_list = []
    if num == 0:
        return bytes([0])
        
    while num > 0:
        # Get the lowest 7 bits
        byte_to_add = num & 0x7F 
        num >>= 7
        # if there are more bytes to come, set the MSB
        if num > 0: 
            byte_to_add |= 0x80
        bytes_list.append(byte_to_add)
    return bytes(bytes_list)

# Helper to send a string prefixed with its 7-bit encoded length
def write_length_prefixed_string(sock, s):
    str_bytes = s.encode('utf-8')
    len_bytes = get_7bit_encoded_int_bytes(len(str_bytes))
    sock.sendall(len_bytes)
    sock.sendall(str_bytes)

class GazeFlowClient:
    # Follow instructions from GazePointer API documentation
    def __init__(self, host="127.0.0.1", port=43333, app_key="AppKeyDemo"):
        self.host = host
        self.port = port
        self.app_key = app_key
        self.sock = None
        self.is_connected = False

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print(f"Connected to GazePointer on {self.host}:{self.port}")

            # 1. Send ResultFormat ("xml")
            result_format = "xml"
            self.sock.sendall(result_format.encode('utf-8'))
            print(f"Sent ResultFormat: {result_format}")

            # 2. Send AppKey (length-prefixed)
            write_length_prefixed_string(self.sock, self.app_key)
            print(f"Sent AppKey: {self.app_key}")

            # 3. Receive connectionInfo
            connection_info = read_length_prefixed_string(self.sock)
            print(f"Received connection info: {connection_info}")

            if connection_info.startswith("ok"):
                self.is_connected = True
                print("GazeFlowAPI connection successful.")
                return True
            else:
                print(f"GazeFlowAPI connection failed: {connection_info}")
                self.disconnect()
                return False

        except Exception as e:
            print(f"Error connecting to GazeFlowAPI: {e}")
            self.disconnect()
            return False

    def receive_gaze_data(self):
        if not self.is_connected or not self.sock:
            return None
        
        try:
            # 4. Receive XML data string (length-prefixed)
            xml_data_str = read_length_prefixed_string(self.sock)

            # 5. Parse XML data
            if not xml_data_str:
                print("Received empty data string, possible disconnect.")
                self.disconnect()
                return None

            root = ET.fromstring(xml_data_str)
            
            gaze_x_elem = root.find('GazeX')
            gaze_y_elem = root.find('GazeY')
            
            gaze_data = {}
            if gaze_x_elem is not None and gaze_y_elem is not None:
                gaze_data['GazeX'] = float(gaze_x_elem.text)
                gaze_data['GazeY'] = float(gaze_y_elem.text)
            else:
                # Handle cases where GazeX/GazeY might be missing
                print("Warning: GazeX or GazeY not found in XML data.")
                return None

            return gaze_data

        except ConnectionAbortedError as e:
            print(f"Connection aborted while receiving data: {e}")
            self.disconnect()
            return None
        except ET.ParseError as e:
            print(f"Error parsing XML data: {e}")
            print(f"Problematic XML string: '{xml_data_str}'")
            return None
        except Exception as e:
            print(f"Error receiving or parsing gaze data: {e}")
            return None


    def disconnect(self):
        self.is_connected = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            finally:
                self.sock.close()
                self.sock = None
                print("Disconnected from GazeFlowAPI.")