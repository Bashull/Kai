import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createStore } from 'zustand';
import { createChatSlice } from '../createChatSlice';
import { createChiSlice } from '../createChiSlice';
import { ChatSlice, ChiSlice } from '../../../types';

type TestStore = ChatSlice & ChiSlice;

function makeStore() {
  return createStore<TestStore>()((...a) => ({
    ...createChatSlice(...a),
    ...createChiSlice(...a),
  }));
}

describe('createChatSlice', () => {
  it('empieza con historial vacío', () => {
    const store = makeStore();
    expect(store.getState().chatHistory).toEqual([]);
  });

  it('addChatMessage añade un mensaje con id y timestamp', () => {
    const store = makeStore();
    store.getState().addChatMessage({ role: 'user', content: 'Hola' });
    const history = store.getState().chatHistory;
    expect(history).toHaveLength(1);
    expect(history[0].role).toBe('user');
    expect(history[0].content).toBe('Hola');
    expect(history[0].id).toBeDefined();
    expect(history[0].timestamp).toBeDefined();
  });

  it('addChatMessage ajusta el CHI (decrementa energía)', () => {
    const store = makeStore();
    const energyBefore = store.getState().chi.energy;
    store.getState().addChatMessage({ role: 'user', content: 'Mensaje de prueba' });
    expect(store.getState().chi.energy).toBeLessThan(energyBefore);
  });

  it('updateLastChatMessage actualiza el contenido del último mensaje', () => {
    const store = makeStore();
    store.getState().addChatMessage({ role: 'model', content: '' });
    store.getState().updateLastChatMessage('Respuesta completa', undefined);
    const last = store.getState().chatHistory.at(-1);
    expect(last?.content).toBe('Respuesta completa');
  });

  it('updateLastChatMessage acumula texto si ya había contenido', () => {
    const store = makeStore();
    store.getState().addChatMessage({ role: 'model', content: 'Hola' });
    store.getState().updateLastChatMessage(' mundo', undefined);
    expect(store.getState().chatHistory.at(-1)?.content).toBe('Hola mundo');
  });

  it('setTyping cambia el estado isTyping', () => {
    const store = makeStore();
    expect(store.getState().isTyping).toBe(false);
    store.getState().setTyping(true);
    expect(store.getState().isTyping).toBe(true);
  });
});
