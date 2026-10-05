import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  QrCode, Search, MapPin, CheckCircle, ArrowRight, Camera,
  VideoOff, RefreshCw, AlertTriangle, XCircle, ShieldCheck
} from 'lucide-react';
import api from '../../services/api';

type CameraState = 'idle' | 'requesting' | 'active' | 'denied' | 'not_found' | 'error';

export default function ScanPage() {
  const [isbnOrId, setIsbnOrId] = useState('');
  const [foundBook, setFoundBook] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [isLoadingBook, setIsLoadingBook] = useState(false);

  // Camera & Permissions State
  const [cameraState, setCameraState] = useState<CameraState>('idle');
  const [cameraErrorDetail, setCameraErrorDetail] = useState('');
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const scanIntervalRef = useRef<any>(null);

  const navigate = useNavigate();

  // Stop camera stream safely and turn off hardware sensor
  const stopCamera = () => {
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
      scanIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraState('idle');
  };

  // Always clean up stream when leaving the page (unmounting)
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  // Request camera permission and start video preview
  const startCamera = async () => {
    setErrorMsg('');
    setCameraErrorDetail('');
    setCameraState('requesting');

    // 1. Check browser support for MediaDevices
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraState('error');
      setCameraErrorDetail('Your browser does not support camera capture via the MediaDevices API.');
      return;
    }

    try {
      // 2. Request user permission via browser prompt
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment', // Prefer rear/shelf camera on mobile/tablet
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });

      // 3. Permission granted: store stream and attach to video preview
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      setCameraState('active');

      // 4. Start optical barcode/QR detection if BarcodeDetector is supported
      startBarcodeDetection();
    } catch (err: any) {
      console.warn('Camera access error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraState('denied');
        setCameraErrorDetail(
          'Camera permission was blocked. To enable, click the lock/settings icon in your browser address bar next to "localhost:5173", toggle Camera to "Allow", and click Retry.'
        );
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraState('not_found');
        setCameraErrorDetail('No physical camera or webcam was detected on this device.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setCameraState('error');
        setCameraErrorDetail('The camera is currently in use by another application. Please close other camera apps and retry.');
      } else {
        setCameraState('error');
        setCameraErrorDetail(err.message || 'Unable to initialize camera video stream.');
      }
    }
  };

  // Barcode / QR detection loop
  const startBarcodeDetection = () => {
    if ('BarcodeDetector' in window) {
      try {
        const barcodeDetector = new (window as any).BarcodeDetector({
          formats: ['qr_code', 'ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e'],
        });

        scanIntervalRef.current = setInterval(async () => {
          if (videoRef.current && videoRef.current.readyState >= 2) {
            try {
              const barcodes = await barcodeDetector.detect(videoRef.current);
              if (barcodes && barcodes.length > 0) {
                const detectedCode = barcodes[0].rawValue;
                if (detectedCode) {
                  stopCamera();
                  setIsbnOrId(detectedCode);
                  handleLookup(detectedCode);
                }
              }
            } catch (detectErr) {
              // Frame scan skip
            }
          }
        }, 400);
      } catch (e) {
        // BarcodeDetector format fallback
      }
    }
  };

  // Lookup book by scanned ID, ISBN, or Title
  const handleLookup = async (idToSearch: string) => {
    if (!idToSearch.trim()) return;
    setErrorMsg('');
    setFoundBook(null);
    setIsLoadingBook(true);

    try {
      const cleanTerm = idToSearch.trim();
      if (/^(?:#?\d|\{|https?:\/\/|\/(?:books|scan)\/)/.test(cleanTerm)) {
        const res=await api.post('/scan/resolve',{scanned_payload:cleanTerm});
        setFoundBook({...res.data.book,rack:res.data.location.rack,shelf:res.data.location.shelf});
      } else {
        const res=await api.get('/books/search/',{params:{query:cleanTerm}});
        if(res.data.length===1)setFoundBook(res.data[0]);
        else setErrorMsg(res.data.length?'Multiple books match. Use the exact ISBN or Book ID.':'No matching book found.');
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Book not found in library catalog. Please verify the code.');
    } finally {
      setIsLoadingBook(false);
    }
  };

  const scanImage = async (file?: File) => {
    if (!file) return;
    stopCamera();setErrorMsg('');
    if(file.size>10*1024*1024){setErrorMsg('Use a QR image up to 10 MB.');return;}
    let decoder: any;
    try {
      const { Html5Qrcode } = await import('html5-qrcode');
      decoder = new Html5Qrcode('qr-file-reader');
      const code = await decoder.scanFile(file, false);
      setIsbnOrId(code);await handleLookup(code);
    } catch { setErrorMsg('Could not decode this image. Use a clear QR image or enter the ISBN.'); }
    finally { if(decoder)decoder.clear(); }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8 pb-16">
      {/* Header */}
      <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 text-center relative overflow-hidden">
        <div className="w-14 h-14 rounded-2xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 mx-auto mb-3 shadow-[0_0_15px_rgba(59,130,246,0.3)]">
          <QrCode className="w-7 h-7" />
        </div>
        <h1 className="text-2xl font-extrabold text-white">Campus Book Scanner & Shelf Locator</h1>
        <p className="text-xs text-gray-400 mt-1 max-w-md mx-auto">
          Scan the QR or Barcode on the spine of any library book to immediately view real-time availability and pinpoint its physical shelf.
        </p>
      </div>

      {/* Main Scanner Card */}
      <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-6 space-y-6">
        {/* Permission Explanation Banner */}
        <div className="bg-blue-950/30 border border-blue-800/50 rounded-xl p-3.5 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div className="text-xs">
            <span className="font-semibold text-blue-200">Camera Permission & Privacy:</span>
            <p className="text-gray-300 mt-0.5 leading-relaxed">
              Camera access is requested only when you click "Start Scanner". Video streams are processed locally in your browser to decode book barcodes and are never stored or transmitted.
            </p>
          </div>
        </div>

        {/* Camera Viewport Area */}
        <div className="w-full min-h-[300px] bg-gray-950 rounded-xl border border-gray-800 relative overflow-hidden flex flex-col items-center justify-center text-center p-4">
          {/* 1. Active Camera Video Feed */}
          <video
            ref={videoRef}
            className={`w-full h-72 object-cover rounded-lg ${cameraState === 'active' ? 'block' : 'hidden'}`}
            autoPlay
            playsInline
            muted
          />

          {/* Active viewfinder overlay crosshair */}
          {cameraState === 'active' && (
            <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center">
              <div className="w-64 h-44 border-2 border-dashed border-cyan-400/80 rounded-xl relative shadow-[0_0_20px_rgba(34,211,238,0.3)]">
                <div className="absolute inset-x-0 h-0.5 bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-pulse" />
              </div>
              <p className="text-[11px] font-semibold text-cyan-300 mt-3 bg-black/60 px-3 py-1 rounded-full backdrop-blur-sm">
                Align barcode or QR code inside frame
              </p>
            </div>
          )}

          {/* 2. Idle State */}
          {cameraState === 'idle' && (
            <div className="py-8 px-4 flex flex-col items-center max-w-sm">
              <div className="w-16 h-16 rounded-full bg-blue-600/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-3">
                <Camera className="w-8 h-8" />
              </div>
              <h3 className="text-sm font-bold text-white mb-1">Camera Scanner Ready</h3>
              <p className="text-xs text-gray-400 mb-4">
                Click below to grant camera access and activate the optical barcode reader.
              </p>
              <button
                type="button"
                onClick={startCamera}
                className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold py-2.5 px-5 rounded-xl transition flex items-center gap-2 shadow-[0_0_15px_rgba(37,99,235,0.4)]"
              >
                <Camera className="w-4 h-4" /> Allow Camera Access & Start Scanner
              </button>
            </div>
          )}

          {/* 3. Requesting State */}
          {cameraState === 'requesting' && (
            <div className="py-12 flex flex-col items-center">
              <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-xs text-blue-300 font-semibold">Requesting camera permissions...</p>
              <p className="text-[11px] text-gray-400 mt-1">Please confirm access in your browser prompt.</p>
            </div>
          )}

          {/* 4. Denied State */}
          {cameraState === 'denied' && (
            <div className="py-8 px-4 flex flex-col items-center max-w-md">
              <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400 mb-3">
                <VideoOff className="w-7 h-7" />
              </div>
              <h3 className="text-sm font-bold text-red-400 mb-1">Camera Permission Blocked</h3>
              <p className="text-xs text-gray-300 mb-4 text-center leading-relaxed">
                {cameraErrorDetail}
              </p>
              <button
                type="button"
                onClick={startCamera}
                className="bg-red-600 hover:bg-red-700 text-white text-xs font-bold py-2 px-4 rounded-xl transition flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" /> Retry Permission Request
              </button>
            </div>
          )}

          {/* 5. Not Found or Error State */}
          {(cameraState === 'not_found' || cameraState === 'error') && (
            <div className="py-8 px-4 flex flex-col items-center max-w-md">
              <div className="w-14 h-14 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 mb-3">
                <AlertTriangle className="w-7 h-7" />
              </div>
              <h3 className="text-sm font-bold text-amber-300 mb-1">
                {cameraState === 'not_found' ? 'No Camera Device Found' : 'Camera Initialization Error'}
              </h3>
              <p className="text-xs text-gray-300 mb-4 text-center leading-relaxed">
                {cameraErrorDetail}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={startCamera}
                  className="bg-gray-800 hover:bg-gray-700 text-white text-xs font-semibold py-2 px-4 rounded-xl transition flex items-center gap-2 border border-gray-700"
                >
                  <RefreshCw className="w-4 h-4" /> Retry
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Camera Control Bar (when camera is active) */}
        {cameraState === 'active' && (
          <div className="flex items-center justify-between bg-[#172033] p-3 rounded-xl border border-gray-800">
            <div className="flex items-center gap-2 text-xs text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span className="font-semibold">Scanner active — Point at barcode</span>
            </div>
            <button
              type="button"
              onClick={stopCamera}
              className="bg-red-600/20 hover:bg-red-600/30 text-red-300 text-xs font-semibold py-1.5 px-3 rounded-lg transition border border-red-500/30 flex items-center gap-1.5"
            >
              <XCircle className="w-3.5 h-3.5" /> Stop Scanner
            </button>
          </div>
        )}

        <label className="block text-sm text-gray-300">Scan QR image<input type="file" accept="image/png,image/jpeg,image/webp" className="block mt-2 text-xs" onChange={e=>void scanImage(e.target.files?.[0])}/></label>
        <div id="qr-file-reader" />

        {/* Manual Code / ISBN Entry Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleLookup(isbnOrId);
          }}
          className="pt-4 border-t border-gray-800/80 flex gap-3"
        >
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={isbnOrId}
              onChange={(e) => setIsbnOrId(e.target.value)}
              placeholder="Or manually enter ISBN, Barcode, or Book Title..."
              className="w-full bg-[#172033] border border-gray-700/60 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={isLoadingBook}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-5 py-2.5 rounded-xl transition shadow-[0_0_10px_rgba(37,99,235,0.4)] disabled:opacity-50"
          >
            {isLoadingBook ? 'Locating...' : 'Locate Shelf'}
          </button>
        </form>

        {/* Error Message Display */}
        {errorMsg && (
          <p className="text-xs text-rose-400 bg-rose-950/30 border border-rose-800/40 p-3 rounded-xl">
            {errorMsg}
          </p>
        )}

        {/* Located Book Result Card with Physical Shelf & Rack Location */}
        {foundBook && (
          <div className="bg-[#172033] border border-blue-500/40 rounded-xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-[0_0_20px_rgba(59,130,246,0.15)] animate-in fade-in duration-300">
            <div className="flex items-center gap-4">
              <div className="w-16 h-22 rounded-lg overflow-hidden bg-gray-900 shrink-0 border border-gray-700/50">
                <img
                  src={foundBook.cover_image || 'https://images-na.ssl-images-amazon.com/images/I/41xShlnTZTL._SX376_BO1,204,203,200_.jpg'}
                  alt={foundBook.title}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              </div>

              <div>
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                  <CheckCircle className="w-3.5 h-3.5" /> Book Identified & Located
                </span>
                <h3 className="text-sm font-bold text-white mt-0.5">{foundBook.title}</h3>
                <p className="text-xs text-gray-400">by {foundBook.author}</p>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  <span className="text-xs bg-blue-900/40 text-blue-300 px-2.5 py-1 rounded font-bold border border-blue-800/40 flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-blue-400" />
                    Physical Rack: {foundBook.rack || 'Not recorded'} • Shelf: {foundBook.shelf || 'Not recorded'}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-semibold ${
                      foundBook.available_copies > 0
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}
                  >
                    {foundBook.available_copies > 0
                      ? `${foundBook.available_copies} Copies Available`
                      : 'Currently Checked Out'}
                  </span>
                </div>
              </div>
            </div>

            <button
              onClick={() => navigate(`/books/${foundBook.id}`)}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold py-2 px-4 rounded-xl transition flex items-center gap-1.5 self-end sm:self-center shrink-0"
            >
              View Full Details <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
