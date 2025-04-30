import numpy as np
from scipy import signal

class ECGProcessor:
    def __init__(self):
        self.sampling_rate = 100  # 100 Hz
        self.window_size = 500    # 5 seconds
    
    def detect_qrs(self, ecg_data):
        """
        Detect QRS complexes in ECG data
        Returns positions of R peaks
        """
        if len(ecg_data) < self.window_size:
            return []
        
        # Simple peak detection (in a real app, would use Pan-Tompkins or similar)
        # Apply bandpass filter to isolate QRS complex frequencies
        b, a = signal.butter(3, [5/50, 15/50], 'bandpass')
        filtered = signal.filtfilt(b, a, ecg_data)
        
        # Square the signal to emphasize peaks
        squared = filtered ** 2
        
        # Moving average integration
        window_size = int(0.150 * self.sampling_rate)  # 150ms window
        integrated = np.convolve(squared, np.ones(window_size)/window_size, mode='same')
        
        # Find peaks
        peaks, _ = signal.find_peaks(integrated, distance=0.5*self.sampling_rate)
        
        return peaks
    
    def calculate_heart_rate(self, peak_indices):
        """Calculate heart rate from R-R intervals"""
        if len(peak_indices) < 2:
            return 0
        
        # Calculate average R-R interval
        rr_intervals = np.diff(peak_indices) / self.sampling_rate  # in seconds
        mean_rr = np.mean(rr_intervals)
        
        # Convert to BPM
        hr = 60 / mean_rr
        
        return round(hr)
    
    def detect_rhythm(self, ecg_signal):
        """
        Detect rhythm type from ECG data
        Returns rhythm classification
        """
        # Get QRS complexes
        peaks = self.detect_qrs(ecg_signal)
        
        # Calculate heart rate
        hr = self.calculate_heart_rate(peaks)
        
        # Not enough peaks to determine rhythm
        
        
        # Calculate RR intervals and their features
        rr_intervals = np.diff(peaks) / self.sampling_rate
        self.rr_intervals = rr_intervals
        
        # Statistical features of RR intervals
        rr_mean = np.mean(rr_intervals)
        rr_std = np.std(rr_intervals)
        rr_cv = rr_std / rr_mean if rr_mean > 0 else 0  # Coefficient of variation
        
        # pNN50: percentage of successive RR intervals that differ by more than 50ms
        diff_rr = np.abs(np.diff(rr_intervals))
        pnn50 = np.sum(diff_rr > 0.05) / len(diff_rr) if len(diff_rr) > 0 else 0
        
        # Calculate spectral features from the RR intervals
        # (simplified frequency domain analysis)
        if len(rr_intervals) >= 10:
            # Resample RR intervals to evenly spaced time series
            rr_x = np.cumsum(rr_intervals)
            rr_y = rr_intervals
            rr_resample = np.linspace(rr_x[0], rr_x[-1], len(rr_intervals))
            rr_interpolated = np.interp(rr_resample, rr_x, rr_y)
            
            # Remove trend
            rr_interpolated = rr_interpolated - np.mean(rr_interpolated)
            
            # Calculate power spectral density
            frequencies, psd = signal.welch(rr_interpolated, fs=1.0, nperseg=min(len(rr_interpolated), 10))
            
            # Define frequency bands
            vlf_mask = (frequencies >= 0.003) & (frequencies < 0.04)  # Very low frequency
            lf_mask = (frequencies >= 0.04) & (frequencies < 0.15)    # Low frequency
            hf_mask = (frequencies >= 0.15) & (frequencies < 0.4)     # High frequency
            
            # Calculate power in each band
            vlf_power = np.sum(psd[vlf_mask]) if np.any(vlf_mask) else 0
            lf_power = np.sum(psd[lf_mask]) if np.any(lf_mask) else 0
            hf_power = np.sum(psd[hf_mask]) if np.any(hf_mask) else 0
            
            # LF/HF ratio (indicator of sympathovagal balance)
            lf_hf_ratio = lf_power / hf_power if hf_power > 0 else 0
        else:
            lf_hf_ratio = 0
            pnn50 = 0
        
        # Rule-based classification with more robust criteria
        if hr > 100:  # Tachycardia
            if rr_cv > 0.2:  # High irregularity
                if pnn50 < 0.1:  # Low beat-to-beat variability
                    self.rhythm_type = "Atrial Flutter"
                else:
                    self.rhythm_type = "Atrial Fibrillation"
            else:  # Regular tachycardia
                self.rhythm_type = "Sinus Tachycardia" 
        elif hr < 60:  # Bradycardia
            if rr_cv > 0.2:
                self.rhythm_type = "Sinus Arrhythmia"
            else:
                self.rhythm_type = "Sinus Bradycardia"
        else:  # Normal rate
            if rr_cv > 0.2:  # Irregular
                if pnn50 > 0.4 and lf_hf_ratio > 2:
                    self.rhythm_type = "Atrial Fibrillation"
                else:
                    self.rhythm_type = "Sinus Arrhythmia"
            else:  # Regular
                self.rhythm_type = "Normal Sinus Rhythm"
        
        return self.rhythm_type