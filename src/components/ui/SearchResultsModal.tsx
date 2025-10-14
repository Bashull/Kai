import React from 'react';
import { useAppStore } from '@/store/useAppStore';
import Modal from '@/components/ui/Modal';
import MarkdownRenderer from '@/components/ui/MarkdownRenderer';
import { Loader2 } from 'lucide-react';

const SearchResultsModal: React.FC = () => {
  const {
    isSearching,
    searchResults,
    showSearchResults,
    closeSearchResults,
    searchQuery,
  } = useAppStore();

  return (
    <Modal
      isOpen={showSearchResults}
      onClose={closeSearchResults}
      title={`Resultados de la Búsqueda para: "${searchQuery}"`}
      size="lg"
    >
      {isSearching && !searchResults && (
        <div className="flex flex-col items-center justify-center min-h-[200px]">
          <Loader2 className="w-12 h-12 animate-spin text-kai-primary" />
          <p className="mt-4 text-text-secondary">Kai está pensando...</p>
        </div>
      )}
      {!isSearching && searchResults && (
        <div className="max-h-[60vh] overflow-y-auto pr-2">
            <MarkdownRenderer content={searchResults} />
        </div>
      )}
    </Modal>
  );
};

export default SearchResultsModal;