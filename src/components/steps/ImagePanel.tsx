import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';
import { generateImages } from '../../services/geminiService';
import { Image as ImageIcon, Sparkles, Download } from 'lucide-react';
import { downloadFile, dataUrlToBlob } from '../../utils/helpers';
import Button from '../ui/Button';
import Modal from '../ui/Modal';
import { GeneratedImage } from '../../types';

const ImagePanel: React.FC = () => {
  const {
    imagePrompt,
    setImagePrompt,
    generatedImages,
    setGeneratedImages,
    isGeneratingImages,
    setIsGeneratingImages
  } = useAppStore();
  const [selectedImage, setSelectedImage] = useState<GeneratedImage | null>(null);


  const handleGenerate = async () => {
    if (!imagePrompt.trim()) return;
    setIsGeneratingImages(true);
    setGeneratedImages([]);
    try {
      const result = await generateImages(imagePrompt);
      setGeneratedImages(result);
    } catch (error) {
      console.error("Image generation failed:", error);
      // Here you could add a user-facing error message, e.g., using a toast notification library
    } finally {
      setIsGeneratingImages(false);
    }
  };

  const handleDownload = async (url: string, prompt: string) => {
    try {
      const blob = await dataUrlToBlob(url);
      const filename = `${prompt.slice(0, 40).replace(/\s/g, '_') || 'kai-image'}.png`;
      downloadFile(blob, filename);
    } catch(error) {
      console.error("Failed to download image:", error);
      // Fallback for browsers that might have issues with fetch on data-uri
      const link = document.createElement('a');
      link.href = url;
      link.download = `${prompt.slice(0, 40).replace(/\s/g, '_') || 'kai-image'}.png`;
      link.click();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex flex-col sm:flex-row gap-4 mb-4">
        <input
          id="image-prompt"
          type="text"
          value={imagePrompt}
          onChange={(e) => setImagePrompt(e.target.value)}
          placeholder="ej: un retrato fotorrealista de un robot sosteniendo un monopatín rojo"
          className="form-input flex-grow"
        />
        <Button onClick={handleGenerate} disabled={isGeneratingImages || !imagePrompt.trim()} loading={isGeneratingImages} icon={Sparkles}>
          Generar
        </Button>
      </div>

      <div className="flex-grow overflow-y-auto pr-2 -mr-2">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {isGeneratingImages && (
            Array.from({ length: 1 }).map((_, i) => (
              <div key={i} className="aspect-square bg-kai-surface rounded-lg flex items-center justify-center animate-pulse">
                <ImageIcon className="w-12 h-12 text-gray-500" />
              </div>
            ))
          )}
          {generatedImages.map((image, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              className="aspect-square rounded-lg overflow-hidden border-2 border-transparent hover:border-kai-primary group relative cursor-pointer"
              onClick={() => setSelectedImage(image)}
            >
              <img src={image.url} alt={image.prompt} className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105" />
               <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center p-4">
                  <p className='text-white text-center font-bold text-sm drop-shadow-lg'>Ver Imagen</p>
              </div>
            </motion.div>
          ))}
        </div>
        {!isGeneratingImages && generatedImages.length === 0 && (
            <div className="col-span-full text-center py-16 text-gray-500">
                <p>Las imágenes generadas aparecerán aquí.</p>
            </div>
        )}
      </div>

      {selectedImage && (
        <Modal 
          isOpen={!!selectedImage} 
          onClose={() => setSelectedImage(null)} 
          title="Vista Previa de Imagen"
          size="xl"
          footer={
            <div className="flex justify-between items-center w-full">
              <p className="text-sm text-text-secondary truncate pr-4">
                <strong>Prompt:</strong> {selectedImage.prompt}
              </p>
              <Button onClick={() => handleDownload(selectedImage.url, selectedImage.prompt)} icon={Download}>
                Descargar Imagen
              </Button>
            </div>
          }
        >
          <img src={selectedImage.url} alt={selectedImage.prompt} className="w-full h-auto object-contain rounded-lg max-h-[70vh]" />
        </Modal>
      )}
    </div>
  );
};

export default ImagePanel;
