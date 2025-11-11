import React, { useState, useCallback, useMemo } from 'react';
import { useAppStore } from '../../store/useAppStore';
import Button from '../ui/Button';
import MarkdownRenderer from '../ui/MarkdownRenderer';
import { Upload, Scan, Wand, X, Loader2 } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

const AnalysisPanel: React.FC = () => {
  const {
    analysisImage, setAnalysisImage,
    analysisPrompt, setAnalysisPrompt,
    isAnalyzing, analysisResult, analyzeImage,
    isEditing, editedImage, editImage,
  } = useAppStore();
  const [isDragging, setIsDragging] = useState(false);

  const onFileChange = (file: File) => {
    if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = (e.target?.result as string).split(',')[1];
            setAnalysisImage(base64);
        };
        reader.readAsDataURL(file);
    }
  };
  
  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); if (e.dataTransfer.files?.[0]) { onFileChange(e.dataTransfer.files[0]); } }, []);
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); e.stopPropagation(); };
  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); };
  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); };
  
  const displayImage = useMemo(() => analysisImage ? `data:image/png;base64,${analysisImage}` : null, [analysisImage]);

  return (
    <div className="h-full flex flex-col">
      <h2 className="text-xl font-bold mb-4">Análisis y Edición de Imágenes</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-grow">
        {/* Input & Controls */}
        <div className="space-y-4 flex flex-col">
            <div 
              className={`file-dropzone flex-grow ${isDragging ? 'border-kai-primary' : ''}`} 
              onDrop={handleDrop} onDragOver={handleDragOver} onDragEnter={handleDragEnter} onDragLeave={handleDragLeave}
            >
              <input type="file" id="analysis-upload" className="hidden" accept="image/*" onChange={(e) => e.target.files && onFileChange(e.target.files[0])} />
              {displayImage ? (
                <div className="relative h-full w-full flex items-center justify-center">
                    <img src={displayImage} alt="Input" className="max-h-full max-w-full object-contain rounded-lg" />
                    <Button onClick={() => setAnalysisImage(null)} variant="danger" size="sm" className="!absolute top-2 right-2 !p-1 !rounded-full h-6 w-6"><X size={14}/></Button>
                </div>
              ) : (
                <label htmlFor="analysis-upload" className="text-center cursor-pointer">
                    <Upload className="mx-auto h-12 w-12 text-text-secondary" />
                    <p className="mt-2 text-sm text-text-secondary">Arrastra una imagen o haz clic para subir</p>
                </label>
              )}
            </div>

            <textarea value={analysisPrompt} onChange={e => setAnalysisPrompt(e.target.value)} placeholder="Describe la imagen, o pide una edición (ej: 'añadele un filtro retro')" className="form-textarea" rows={3} />
            
            <div className="flex gap-2">
                <Button onClick={analyzeImage} disabled={isAnalyzing || isEditing || !analysisImage} loading={isAnalyzing} icon={Scan} className="flex-1">Analizar</Button>
                <Button onClick={editImage} disabled={isAnalyzing || isEditing || !analysisImage || !analysisPrompt} loading={isEditing} icon={Wand} className="flex-1">Editar</Button>
            </div>
        </div>

        {/* Output */}
        <div className="flex flex-col items-center justify-center bg-kai-surface/50 rounded-lg p-4 border border-border-color">
            <AnimatePresence mode="wait">
                {(isAnalyzing || isEditing) ? (
                    <motion.div key="loading" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="text-center">
                        <Loader2 className="h-12 w-12 text-kai-primary animate-spin mb-4" />
                        <p className="font-semibold">{isAnalyzing ? 'Analizando...' : 'Editando...'}</p>
                    </motion.div>
                ) : editedImage ? (
                    <motion.div key="edited" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="w-full h-full">
                        <img src={editedImage} alt="Edited result" className="w-full h-full object-contain rounded-lg" />
                    </motion.div>
                ) : analysisResult ? (
                    <motion.div key="analysis" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="w-full h-full overflow-y-auto">
                        <MarkdownRenderer content={analysisResult} />
                    </motion.div>
                ) : (
                     <motion.div key="placeholder" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="text-center text-text-secondary">
                        <p>Los resultados del análisis o la edición aparecerán aquí.</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default AnalysisPanel;
