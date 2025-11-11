import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { useAppStore } from '../../store/useAppStore';
import { generateCode } from '../../services/geminiService';
import { CodeLanguage } from '../../types';
import { Sparkles, Copy, Download } from 'lucide-react';
import { copyToClipboard, downloadFile } from '../../utils/helpers';
import Button from '../ui/Button';

const languageOptions: { value: CodeLanguage; label: string, extension: string }[] = [
  { value: 'javascript', label: 'JavaScript', extension: 'js' },
  { value: 'typescript', label: 'TypeScript', extension: 'ts' },
  { value: 'python', label: 'Python', extension: 'py' },
  { value: 'html', label: 'HTML', extension: 'html' },
  { value: 'css', label: 'CSS', extension: 'css' },
  { value: 'json', label: 'JSON', extension: 'json' },
  { value: 'markdown', label: 'Markdown', extension: 'md' },
];

const CodePanel: React.FC = () => {
  const {
    codePrompt,
    setCodePrompt,
    generatedCode,
    setGeneratedCode,
    codeLanguage,
    setCodeLanguage,
    isGeneratingCode,
    setIsGeneratingCode
  } = useAppStore();
  const [copyStatus, setCopyStatus] = useState(false);


  const handleGenerate = async () => {
    if (!codePrompt.trim()) return;
    setIsGeneratingCode(true);
    setGeneratedCode(`// Generating code for: ${codePrompt}...`);
    try {
      const result = await generateCode(codePrompt, codeLanguage);
      setGeneratedCode(result);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setGeneratedCode(`// Error: ${errorMessage}`);
    } finally {
      setIsGeneratingCode(false);
    }
  };

  const handleCopy = () => {
    if(!generatedCode) return;
    copyToClipboard(generatedCode).then(success => {
        if (success) {
            setCopyStatus(true);
            setTimeout(() => setCopyStatus(false), 2000);
        }
    });
  };

  const handleDownload = () => {
      if(!generatedCode) return;
      const extension = languageOptions.find(l => l.value === codeLanguage)?.extension || 'txt';
      downloadFile(generatedCode, `kai-code.${extension}`);
  }

  return (
    <div className="flex flex-col h-full">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="md:col-span-2">
            <label htmlFor="code-prompt" className="form-label">
              Descripción del Código
            </label>
            <input
              id="code-prompt"
              type="text"
              value={codePrompt}
              onChange={(e) => setCodePrompt(e.target.value)}
              placeholder="ej: un componente de botón en React con estado de carga"
              className="form-input"
            />
          </div>
          <div>
            <label htmlFor="language" className="form-label">
              Lenguaje
            </label>
            <select
              id="language"
              value={codeLanguage}
              onChange={(e) => setCodeLanguage(e.target.value as CodeLanguage)}
              className="form-select"
            >
              {languageOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <Button 
          onClick={handleGenerate} 
          disabled={isGeneratingCode || !codePrompt.trim()} 
          loading={isGeneratingCode} 
          icon={Sparkles}
          className="mb-4 w-full md:w-auto"
        >
          Generar Código
        </Button>
      

      <div className="relative flex-grow border border-border-color rounded-xl overflow-hidden group">
          <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
              <Button onClick={handleCopy} variant="secondary" size="sm" className="w-24">
                {copyStatus ? '¡Copiado!' : <><Copy size={14} className="mr-1"/> Copiar</>}
              </Button>
              <Button onClick={handleDownload} variant="secondary" size="sm" icon={Download}>
                 Descargar
              </Button>
          </div>
          <Editor
              height="100%"
              language={codeLanguage}
              value={generatedCode}
              onMount={(editor) => editor.focus()}
              theme="vs-dark"
              options={{
              minimap: { enabled: false },
              fontSize: 14,
              wordWrap: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              }}
          />
      </div>
    </div>
  );
};

export default CodePanel;
