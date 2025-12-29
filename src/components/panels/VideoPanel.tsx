import React, { useState, useCallback, useMemo } from 'react';
import { useAppStore } from '../../store/useAppStore';
import Button from '../ui/Button';
import { Video, Sparkles, Upload, X, Loader2 } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

const VideoPanel: React.FC = () => {
    const {
        videoPrompt, setVideoPrompt,
        inputImage, setInputImage,
        videoAspectRatio, setVideoAspectRatio,
        isGeneratingVideo, videoGenerationProgress,
        generatedVideoUrl, generateVideo,
    } = useAppStore();
    const [isDragging, setIsDragging] = useState(false);

    const onFileChange = (file: File) => {
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => setInputImage(e.target?.result as string);
            reader.readAsDataURL(file);
        }
    };

    const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            onFileChange(e.dataTransfer.files[0]);
        }
    }, []);

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); e.stopPropagation(); };
    const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); };
    const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); };

    const base64Image = useMemo(() => {
        return inputImage?.split(',')[1] || null;
    }, [inputImage]);

    return (
        <div className="h-full flex flex-col">
            <h2 className="text-xl font-bold mb-4">Generador de Vídeo (Veo)</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-grow">
                {/* Controls */}
                <div className="space-y-4">
                    <textarea value={videoPrompt} onChange={e => setVideoPrompt(e.target.value)} placeholder="Prompt del vídeo (ej: un coche deportivo futurista conduciendo por Marte)" className="form-textarea" rows={4} />
                    
                    <div className={`file-dropzone ${isDragging ? 'border-kai-primary' : ''}`} onDrop={handleDrop} onDragOver={handleDragOver} onDragEnter={handleDragEnter} onDragLeave={handleDragLeave}>
                        <input type="file" id="image-upload" className="hidden" accept="image/*" onChange={(e) => e.target.files && onFileChange(e.target.files[0])} />
                        {inputImage ? (
                            <div className="relative">
                                <img src={inputImage} alt="Input" className="h-24 object-contain rounded-lg" />
                                <Button onClick={() => setInputImage(null)} variant="danger" size="sm" className="!absolute -top-2 -right-2 !p-1 !rounded-full h-6 w-6"><X size={14}/></Button>
                            </div>
                        ) : (
                            <label htmlFor="image-upload" className="text-center cursor-pointer">
                                <Upload className="mx-auto h-8 w-8 text-text-secondary" />
                                <p className="mt-1 text-sm text-text-secondary">Arrastra una imagen aquí o haz clic para subir una (opcional)</p>
                            </label>
                        )}
                    </div>
                    
                    <div>
                        <label className="form-label">Relación de Aspecto</label>
                        <div className="flex gap-2">
                            <Button onClick={() => setVideoAspectRatio('16:9')} variant={videoAspectRatio === '16:9' ? 'primary' : 'secondary'} size="sm">Paisaje (16:9)</Button>
                            <Button onClick={() => setVideoAspectRatio('9:16')} variant={videoAspectRatio === '9:16' ? 'primary' : 'secondary'} size="sm">Retrato (9:16)</Button>
                        </div>
                    </div>

                    <Button onClick={generateVideo} disabled={isGeneratingVideo} loading={isGeneratingVideo} icon={Sparkles} className="w-full">
                        Generar Vídeo
                    </Button>
                     <p className="text-xs text-text-secondary text-center">La generación de vídeo con Veo requiere una clave de API con acceso y puede tardar varios minutos en completarse.</p>
                </div>
                
                {/* Output */}
                <div className="flex flex-col items-center justify-center bg-kai-surface/50 rounded-lg p-4 border border-border-color">
                    <AnimatePresence mode="wait">
                        {isGeneratingVideo && (
                            <motion.div key="progress" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="text-center">
                                <Loader2 className="h-12 w-12 text-kai-primary animate-spin mb-4" />
                                <p className="font-semibold">Generando vídeo...</p>
                                <p className="text-sm text-text-secondary mt-2 max-w-xs">{videoGenerationProgress}</p>
                            </motion.div>
                        )}
                        {!isGeneratingVideo && generatedVideoUrl && (
                             <motion.div key="video" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="w-full">
                                <video src={generatedVideoUrl} controls autoPlay loop className="w-full rounded-lg" />
                            </motion.div>
                        )}
                         {!isGeneratingVideo && !generatedVideoUrl && (
                            <motion.div key="placeholder" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="text-center text-text-secondary">
                                <Video className="h-16 w-16 mx-auto mb-4"/>
                                <p>El vídeo generado aparecerá aquí.</p>
                            </motion.div>
                         )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
};

export default VideoPanel;
