import numpy as np
import pandas as pd
import os
import struct
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from scipy import io as sio  # Add this import for .mat file support

class ECGDataLoader:
    def __init__(self, parent=None):
        self.parent = parent
        self.current_file = None
        self.data = None
        self.sampling_rate = 100  # Default, can be adjusted
        self.last_directory = "sample_data"  # Default to sample_data directory
        
    def load_file(self, file_path=None):
        """Load ECG data from a file"""
        if file_path is None:
            # Start in the last directory if it exists
            start_dir = self.last_directory if hasattr(self, 'last_directory') and os.path.exists(self.last_directory) else ""
            
            file_path, _ = QFileDialog.getOpenFileName(
                self.parent,
                "Open ECG Data File",
                start_dir,
                # Add .dat to the file filter options
                "All Supported Files (*.csv *.txt *.mat *.dat);;CSV Files (*.csv);;Text Files (*.txt);;MATLAB Files (*.mat);;DAT Files (*.dat);;All Files (*.*)"
            )
            
        if not file_path:
            return None
            
        try:
            # Remember this directory for next time
            self.last_directory = os.path.dirname(file_path)
            
            # Determine file type and load accordingly
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.csv':
                data = self._load_csv(file_path)
            elif ext == '.txt':
                data = self._load_txt(file_path)
            elif ext == '.mat':
                data = self._load_mat(file_path)
            elif ext == '.dat':
                data = self._load_dat(file_path)
            else:
                # Try CSV format by default
                data = self._load_csv(file_path)
                
            self.current_file = file_path
            self.data = data
            return data
            
        except Exception as e:
            if self.parent:
                QMessageBox.critical(
                    self.parent,
                    "Error Loading File",
                    f"Could not load the file: {str(e)}"
                )
            return None
    
    def _load_csv(self, file_path):
        """Load data from a CSV file"""
        try:
            # Try to load with pandas first
            df = pd.read_csv(file_path)
            
            # Check for common column naming patterns
            if 'ecg' in df.columns:
                ecg_data = df['ecg'].values
            elif 'value' in df.columns:
                ecg_data = df['value'].values
            elif 'signal' in df.columns:
                ecg_data = df['signal'].values
            else:
                # Assume first numeric column contains ECG data
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        ecg_data = df[col].values
                        break
                else:
                    raise ValueError("Could not find numeric ECG data column")
            
            # Create time array based on sampling rate
            time = np.arange(0, len(ecg_data) / self.sampling_rate, 1.0/self.sampling_rate)
            
            # Truncate time if it's longer than ecg_data
            if len(time) > len(ecg_data):
                time = time[:len(ecg_data)]
                
            return {'time': time, 'ecg': ecg_data}
        
        except Exception:
            # Fallback to numpy if pandas fails
            data = np.loadtxt(file_path, delimiter=',')
            
            if data.ndim == 1:
                # If only one column, assume it's ECG data
                ecg_data = data
                time = np.arange(0, len(ecg_data) / self.sampling_rate, 1.0/self.sampling_rate)
            else:
                # Assume first column is time and second is ECG
                time = data[:, 0]
                ecg_data = data[:, 1]
                
                # Estimate sampling rate from time column
                if len(time) > 1:
                    avg_diff = np.mean(np.diff(time))
                    if avg_diff > 0:
                        self.sampling_rate = 1.0 / avg_diff
                
            return {'time': time, 'ecg': ecg_data}
    
    def _load_txt(self, file_path):
        """Load data from a text file"""
        try:
            data = np.loadtxt(file_path)
            
            if data.ndim == 1:
                ecg_data = data
                time = np.arange(0, len(ecg_data) / self.sampling_rate, 1.0/self.sampling_rate)
            else:
                # Assume first column is time and second is ECG
                time = data[:, 0]
                ecg_data = data[:, 1]
            
            return {'time': time, 'ecg': ecg_data}
        except:
            # Try reading as CSV with different delimiters
            return self._load_csv(file_path)
    
    def _load_mat(self, file_path):
        """Load data from a MATLAB .mat file"""
        try:
            # Load the .mat file
            mat_data = sio.loadmat(file_path)
            
            # Identify potential ECG data variables
            ecg_data = None
            time = None
            
            # Look for common variable names for ECG data
            ecg_var_names = ['ecg', 'ECG', 'ecgdata', 'ECGData', 'signal', 'data']
            time_var_names = ['time', 'Time', 't', 'T']
            
            # First try to find ECG data
            for name in ecg_var_names:
                if name in mat_data and isinstance(mat_data[name], np.ndarray):
                    ecg_data = mat_data[name]
                    # Flatten if it's not a 1D array
                    if ecg_data.ndim > 1:
                        ecg_data = ecg_data.flatten() if ecg_data.size > 0 else ecg_data.ravel()
                    break
            
            # If still not found, try the biggest numeric array that's not time
            if ecg_data is None:
                biggest_var = None
                biggest_size = 0
                
                for var_name, var_value in mat_data.items():
                    # Skip metadata variables (which start with '__')
                    if var_name.startswith('__'):
                        continue
                    
                    if isinstance(var_value, np.ndarray) and var_value.size > biggest_size:
                        if var_name not in time_var_names:
                            biggest_var = var_name
                            biggest_size = var_value.size
                
                if biggest_var:
                    ecg_data = mat_data[biggest_var]
                    if ecg_data.ndim > 1:
                        ecg_data = ecg_data.flatten() if ecg_data.size > 0 else ecg_data.ravel()
            
            # If still no ECG data found
            if ecg_data is None:
                raise ValueError("Could not find ECG data in the .mat file")
            
            # Look for time data
            for name in time_var_names:
                if name in mat_data and isinstance(mat_data[name], np.ndarray):
                    time = mat_data[name]
                    if time.ndim > 1:
                        time = time.flatten() if time.size > 0 else time.ravel()
                    # Only use if length matches ECG data
                    if len(time) != len(ecg_data):
                        time = None
                    else:
                        break
            
            # If time array not found or invalid length, create one
            if time is None:
                # Try to get sampling rate from file if available
                fs_var_names = ['fs', 'Fs', 'samplerate', 'sampleRate', 'sample_rate']
                sampling_rate = 250  # Default sampling rate
                
                for name in fs_var_names:
                    if name in mat_data and np.isscalar(mat_data[name]):
                        sampling_rate = float(mat_data[name])
                        break
                        
                # Create time array based on sampling rate
                time = np.arange(0, len(ecg_data) / sampling_rate, 1.0/sampling_rate)
                
                # Truncate time if it's longer than ecg_data
                if len(time) > len(ecg_data):
                    time = time[:len(ecg_data)]
            
            # Return the data in the same format as other loaders
            return {'time': time, 'ecg': ecg_data}
            
        except Exception as e:
            raise ValueError(f"Error loading .mat file: {str(e)}")
    
    # Add this new method to load .dat files
    def _load_dat(self, file_path):
        """Load data from a .dat file (ECG/PhysioNet format)"""
        try:
            # First try to load as PhysioNet format (binary)
            try:
                # Check for header file (.hea)
                header_file = os.path.splitext(file_path)[0] + '.hea'
                if os.path.exists(header_file):
                    return self._load_physionet_dat(file_path, header_file)
            except:
                pass
                
            # If that fails, try as a plain binary file
            with open(file_path, 'rb') as f:
                # Try to detect format - check first few bytes
                header = f.read(8)
                f.seek(0)  # Reset to beginning
                
                # Try int16 format (common for ECG)
                if len(header) >= 2:
                    try:
                        # Read as int16 samples
                        data = np.fromfile(f, dtype=np.int16)
                        
                        # Generate time array (assume 250Hz sampling rate as default)
                        sampling_rate = 250.0
                        time = np.arange(0, len(data) / sampling_rate, 1.0/sampling_rate)
                        
                        # Truncate time if it's longer than data
                        if len(time) > len(data):
                            time = time[:len(data)]
                            
                        return {'time': time, 'ecg': data}
                    except:
                        f.seek(0)  # Reset to beginning
                
                # Try float32 format (also common)
                if len(header) >= 4:
                    try:
                        # Read as float32 samples
                        f.seek(0)
                        data = np.fromfile(f, dtype=np.float32)
                        
                        # Generate time array (assume 250Hz sampling rate as default)
                        sampling_rate = 250.0
                        time = np.arange(0, len(data) / sampling_rate, 1.0/sampling_rate)
                        
                        # Truncate time if it's longer than data
                        if len(time) > len(data):
                            time = time[:len(data)]
                            
                        return {'time': time, 'ecg': data}
                    except:
                        pass
                        
                # If we get here, try as a text file as last resort
                try:
                    f.seek(0)
                    # Read lines and parse as numbers
                    lines = f.readlines()
                    data = []
                    for line in lines:
                        try:
                            # Try to decode and convert to float
                            value = float(line.strip())
                            data.append(value)
                        except:
                            pass  # Skip lines that can't be parsed
                            
                    if data:
                        data = np.array(data)
                        sampling_rate = 250.0
                        time = np.arange(0, len(data) / sampling_rate, 1.0/sampling_rate)
                        return {'time': time, 'ecg': data}
                except:
                    pass
                    
            # If all attempts fail
            raise ValueError("Could not determine the format of the .dat file")
            
        except Exception as e:
            raise ValueError(f"Error loading .dat file: {str(e)}")
            
    def _load_physionet_dat(self, dat_file, header_file):
        """Load a PhysioNet format .dat file with corresponding .hea header"""
        try:
            # Parse the header file
            with open(header_file, 'r') as f:
                header_lines = f.readlines()
            
            # Extract sampling rate and format information from header
            record_name = None
            num_signals = 0
            sampling_rate = 250.0  # Default
            samples_per_signal = 0
            format_type = '16'  # Default format (16-bit integers)
            
            for i, line in enumerate(header_lines):
                if i == 0:  # First line contains record info
                    parts = line.strip().split()
                    if len(parts) > 1:
                        record_name = parts[0]
                    if len(parts) > 2:
                        num_signals = int(parts[1])
                    if len(parts) > 3:
                        sampling_rate = float(parts[2])
                elif i <= num_signals:  # Signal specification lines
                    parts = line.strip().split()
                    if len(parts) > 1:
                        file_name = parts[0]
                        if len(parts) > 2:
                            format_type = parts[1]
                        if len(parts) > 3:
                            samples_per_signal = max(samples_per_signal, int(float(parts[3])))
            
            # Determine the data type based on format
            if format_type == '16':
                dtype = np.int16
            elif format_type == '32':
                dtype = np.int32
            elif format_type == '61':
                dtype = np.float32
            elif format_type == '80':
                dtype = np.float64
            elif format_type == '160':
                dtype = np.int16
            elif format_type == '212':
                # Special case for 12-bit format
                return self._load_212_format(dat_file, num_signals, samples_per_signal)
            elif format_type == '310':
                # Special case for 10-bit format
                return self._load_310_format(dat_file, num_signals, samples_per_signal)
            else:
                dtype = np.int16  # Default to 16-bit
            
            # Read the binary data
            with open(dat_file, 'rb') as f:
                data = np.fromfile(f, dtype=dtype)
            
            # Reshape if multiple signals
            if num_signals > 1:
                data = data.reshape(-1, num_signals)
                # Use only the first channel for now
                ecg_data = data[:, 0]
            else:
                ecg_data = data
            
            # Create time array
            time = np.arange(0, len(ecg_data) / sampling_rate, 1.0/sampling_rate)
            if len(time) > len(ecg_data):
                time = time[:len(ecg_data)]
            
            return {'time': time, 'ecg': ecg_data}
            
        except Exception as e:
            raise ValueError(f"Error parsing PhysioNet format: {str(e)}")
    
    def _load_212_format(self, dat_file, num_signals, samples_per_signal):
        """Load 212 format (12-bit) PhysioNet data"""
        try:
            # For 212 format, each pair of samples is stored in 3 bytes
            with open(dat_file, 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint8)
            
            # Calculate number of samples (2 samples per 3 bytes)
            num_samples = len(data) // 3 * 2
            
            # Process the bytes to extract the 12-bit samples
            samples = np.zeros(num_samples, dtype=np.int16)
            
            for i in range(0, num_samples//2):
                byte1 = data[i*3]
                byte2 = data[i*3+1]
                byte3 = data[i*3+2]
                
                # First sample = (byte1 << 4) + (byte2 & 0xF0) >> 4
                # Second sample = (byte3 << 4) + (byte2 & 0x0F)
                samples[i*2] = (byte1 << 4) + ((byte2 & 0xF0) >> 4)
                samples[i*2+1] = (byte3 << 4) + (byte2 & 0x0F)
                
                # Convert to signed (two's complement for 12 bits)
                if samples[i*2] > 2047:
                    samples[i*2] -= 4096
                if samples[i*2+1] > 2047:
                    samples[i*2+1] -= 4096
            
            # Reshape if multiple signals
            if num_signals > 1:
                samples_per_channel = num_samples // num_signals
                samples = samples[:samples_per_channel * num_signals].reshape(-1, num_signals)
                # Use first channel
                ecg_data = samples[:, 0]
            else:
                ecg_data = samples
            
            # Create time array (assuming 250Hz)
            sampling_rate = 250.0
            time = np.arange(0, len(ecg_data) / sampling_rate, 1.0/sampling_rate)
            if len(time) > len(ecg_data):
                time = time[:len(ecg_data)]
            
            return {'time': time, 'ecg': ecg_data}
            
        except Exception as e:
            raise ValueError(f"Error loading 212 format: {str(e)}")
    
    def _load_310_format(self, dat_file, num_signals, samples_per_signal):
        """Load 310 format (10-bit) PhysioNet data"""
        # Implementation for 310 format - simplified placeholder
        # This would need a more complete implementation for real use
        try:
            with open(dat_file, 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint8)
            
            # Process bytes to extract 10-bit samples - simplified approach
            # For detailed implementation, see PhysioNet's WFDB library
            
            # Create placeholder data
            ecg_data = np.zeros(len(data)//2, dtype=np.float32)
            for i in range(len(ecg_data)):
                if i*2+1 < len(data):
                    # Simplified: just combine pairs of bytes
                    ecg_data[i] = data[i*2] + (data[i*2+1] << 8)
            
            # Create time array
            sampling_rate = 250.0
            time = np.arange(0, len(ecg_data) / sampling_rate, 1.0/sampling_rate)
            if len(time) > len(ecg_data):
                time = time[:len(ecg_data)]
            
            return {'time': time, 'ecg': ecg_data}
            
        except Exception as e:
            raise ValueError(f"Error loading 310 format: {str(e)}")
    
    def get_file_info(self):
        """Get basic info about the loaded file"""
        if self.data is None:
            return "No data loaded"
        
        ecg_data = self.data['ecg']
        duration = len(ecg_data) / self.sampling_rate
        
        info = {
            'filename': os.path.basename(self.current_file) if self.current_file else "Unknown",
            'samples': len(ecg_data),
            'duration': f"{duration:.1f} seconds",
            'sampling_rate': f"{self.sampling_rate} Hz",
            'min': f"{np.min(ecg_data):.2f}",
            'max': f"{np.max(ecg_data):.2f}",
            'mean': f"{np.mean(ecg_data):.2f}"
        }
        
        return info