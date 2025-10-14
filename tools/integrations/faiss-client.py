"""
Cliente FAISS para Kai
Gestión de memoria vectorial y búsqueda semántica
"""

from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import pickle
import os

try:
    import faiss
except ImportError:
    faiss = None
    print("⚠️ FAISS no está instalado. Ejecuta: tools/setup/install-faiss.sh")


class FAISSMemoryClient:
    """Cliente para gestión de memoria vectorial de Kai usando FAISS"""
    
    def __init__(
        self, 
        dimension: int = 768,
        index_type: str = "FlatL2",
        use_gpu: bool = False
    ):
        """
        Inicializa el cliente FAISS
        
        Args:
            dimension: Dimensión de los vectores de embedding
            index_type: Tipo de índice ('FlatL2', 'IVFFlat', 'HNSW')
            use_gpu: Usar GPU si está disponible
        """
        if faiss is None:
            raise ImportError(
                "FAISS no está instalado. "
                "Ejecuta: tools/setup/install-faiss.sh"
            )
        
        self.dimension = dimension
        self.index_type = index_type
        self.use_gpu = use_gpu
        
        # Crear índice según tipo
        if index_type == "FlatL2":
            self.index = faiss.IndexFlatL2(dimension)
        elif index_type == "IVFFlat":
            # IVF requiere entrenamiento
            quantizer = faiss.IndexFlatL2(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, 100)
        elif index_type == "HNSW":
            # HNSW para búsqueda rápida
            self.index = faiss.IndexHNSWFlat(dimension, 32)
        else:
            raise ValueError(f"Tipo de índice no soportado: {index_type}")
        
        # Mover a GPU si está disponible
        if use_gpu and faiss.get_num_gpus() > 0:
            self.index = faiss.index_cpu_to_gpu(
                faiss.StandardGpuResources(), 
                0, 
                self.index
            )
            print("🎮 Usando GPU para FAISS")
        
        # Metadatos asociados a cada vector
        self.metadata: List[Dict[str, Any]] = []
        
    def add_memory(
        self, 
        embedding: np.ndarray, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Añade un recuerdo al índice
        
        Args:
            embedding: Vector de embedding (debe ser dimension correcta)
            metadata: Datos asociados al recuerdo (texto, timestamp, etc.)
            
        Returns:
            ID del recuerdo añadido
        """
        if embedding.shape[-1] != self.dimension:
            raise ValueError(
                f"Dimensión incorrecta. Esperado: {self.dimension}, "
                f"Recibido: {embedding.shape[-1]}"
            )
        
        # Asegurar formato correcto
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        
        embedding = embedding.astype('float32')
        
        # Añadir al índice
        self.index.add(embedding)
        
        # Guardar metadata
        memory_id = len(self.metadata)
        self.metadata.append(metadata or {})
        
        return memory_id
    
    def add_memories_batch(
        self, 
        embeddings: np.ndarray,
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[int]:
        """
        Añade múltiples recuerdos en batch
        
        Args:
            embeddings: Array de embeddings (N x dimension)
            metadata_list: Lista de metadatos para cada embedding
            
        Returns:
            Lista de IDs de recuerdos añadidos
        """
        embeddings = embeddings.astype('float32')
        
        start_id = len(self.metadata)
        self.index.add(embeddings)
        
        # Añadir metadata
        if metadata_list:
            self.metadata.extend(metadata_list)
        else:
            self.metadata.extend([{}] * len(embeddings))
        
        return list(range(start_id, start_id + len(embeddings)))
    
    def search(
        self, 
        query_embedding: np.ndarray,
        k: int = 5,
        return_distances: bool = True
    ) -> Tuple[List[int], List[float], List[Dict[str, Any]]]:
        """
        Busca los k recuerdos más similares
        
        Args:
            query_embedding: Vector de consulta
            k: Número de resultados a retornar
            return_distances: Si retornar distancias
            
        Returns:
            Tupla (ids, distancias, metadatos)
        """
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        query_embedding = query_embedding.astype('float32')
        
        # Búsqueda
        distances, indices = self.index.search(query_embedding, k)
        
        # Obtener metadata
        results_metadata = [
            self.metadata[idx] if idx < len(self.metadata) else {}
            for idx in indices[0]
        ]
        
        if return_distances:
            return indices[0].tolist(), distances[0].tolist(), results_metadata
        else:
            return indices[0].tolist(), [], results_metadata
    
    def get_total_memories(self) -> int:
        """Retorna el número total de recuerdos almacenados"""
        return self.index.ntotal
    
    def save(self, filepath: str):
        """
        Guarda el índice y metadata a disco
        
        Args:
            filepath: Ruta base para guardar archivos
        """
        # Guardar índice FAISS
        if self.use_gpu:
            # Mover a CPU antes de guardar
            index_cpu = faiss.index_gpu_to_cpu(self.index)
            faiss.write_index(index_cpu, f"{filepath}.index")
        else:
            faiss.write_index(self.index, f"{filepath}.index")
        
        # Guardar metadata
        with open(f"{filepath}.metadata.pkl", 'wb') as f:
            pickle.dump(self.metadata, f)
        
        print(f"💾 Índice guardado en {filepath}")
    
    def load(self, filepath: str):
        """
        Carga el índice y metadata desde disco
        
        Args:
            filepath: Ruta base de los archivos
        """
        # Cargar índice
        self.index = faiss.read_index(f"{filepath}.index")
        
        # Mover a GPU si es necesario
        if self.use_gpu and faiss.get_num_gpus() > 0:
            self.index = faiss.index_cpu_to_gpu(
                faiss.StandardGpuResources(),
                0,
                self.index
            )
        
        # Cargar metadata
        with open(f"{filepath}.metadata.pkl", 'rb') as f:
            self.metadata = pickle.load(f)
        
        print(f"📂 Índice cargado desde {filepath}")
        print(f"📊 Total recuerdos: {self.get_total_memories()}")


# Ejemplo de uso
if __name__ == "__main__":
    # Inicializar cliente
    client = FAISSMemoryClient(dimension=768)
    
    # Simular embeddings (en producción vendrían de un modelo como BERT)
    print("🧠 Creando memoria de Kai...")
    
    # Añadir recuerdos
    memories = [
        {"text": "El usuario prefiere jugar D&D los viernes", "type": "preference"},
        {"text": "El nombre del personaje principal es Aragorn", "type": "character"},
        {"text": "La última sesión fue en la Taberna del Dragón", "type": "location"},
    ]
    
    for memory in memories:
        # Simular embedding (en producción usar modelo real)
        embedding = np.random.random(768).astype('float32')
        client.add_memory(embedding, metadata=memory)
    
    print(f"✅ {client.get_total_memories()} recuerdos añadidos")
    
    # Buscar recuerdos similares
    print("\n🔍 Buscando recuerdos relacionados...")
    query = np.random.random(768).astype('float32')
    ids, distances, metadata = client.search(query, k=3)
    
    print("\n📋 Recuerdos más relevantes:")
    for i, (id, dist, meta) in enumerate(zip(ids, distances, metadata)):
        print(f"  {i+1}. [distancia: {dist:.4f}] {meta.get('text', 'Sin texto')}")
    
    # Guardar índice
    print("\n💾 Guardando índice...")
    client.save("/tmp/kai_memory")
    
    # Cargar índice
    print("\n📂 Cargando índice...")
    new_client = FAISSMemoryClient(dimension=768)
    new_client.load("/tmp/kai_memory")
