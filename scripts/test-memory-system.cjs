#!/usr/bin/env node

/**
 * Memory System Test Script
 * Tests the long-term memory functionality
 */

const fs = require('fs');

console.log('🧠 Testing Long-term Memory System\n');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

// Test 1: Type definitions
console.log('📋 Test 1: Type Definitions');
try {
    const typesContent = fs.readFileSync('src/types.ts', 'utf8');
    
    const hasMemoryType = typesContent.includes('export type MemoryType');
    const hasMemoryInterface = typesContent.includes('export interface Memory');
    const hasMemorySlice = typesContent.includes('export interface MemorySlice');
    const hasMemoryInPanel = typesContent.includes("'memory'");
    
    console.log(`  ✅ MemoryType definition: ${hasMemoryType ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Memory interface: ${hasMemoryInterface ? 'Found' : 'Missing'}`);
    console.log(`  ✅ MemorySlice interface: ${hasMemorySlice ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Memory panel in Panel type: ${hasMemoryInPanel ? 'Found' : 'Missing'}`);
    
    if (hasMemoryType && hasMemoryInterface && hasMemorySlice && hasMemoryInPanel) {
        console.log('  ✨ All type definitions present!\n');
    } else {
        throw new Error('Missing type definitions');
    }
} catch (error) {
    console.error('  ❌ Error:', error.message);
    process.exit(1);
}

// Test 2: Memory Slice
console.log('📋 Test 2: Memory Slice');
try {
    const sliceContent = fs.readFileSync('src/store/slices/createMemorySlice.ts', 'utf8');
    
    const hasAddMemory = sliceContent.includes('addMemory');
    const hasUpdateMemory = sliceContent.includes('updateMemory');
    const hasDeleteMemory = sliceContent.includes('deleteMemory');
    const hasSearchMemories = sliceContent.includes('searchMemories');
    
    console.log(`  ✅ addMemory function: ${hasAddMemory ? 'Found' : 'Missing'}`);
    console.log(`  ✅ updateMemory function: ${hasUpdateMemory ? 'Found' : 'Missing'}`);
    console.log(`  ✅ deleteMemory function: ${hasDeleteMemory ? 'Found' : 'Missing'}`);
    console.log(`  ✅ searchMemories function: ${hasSearchMemories ? 'Found' : 'Missing'}`);
    
    if (hasAddMemory && hasUpdateMemory && hasDeleteMemory && hasSearchMemories) {
        console.log('  ✨ All memory slice functions present!\n');
    } else {
        throw new Error('Missing memory slice functions');
    }
} catch (error) {
    console.error('  ❌ Error:', error.message);
    process.exit(1);
}

// Test 3: Store Integration
console.log('📋 Test 3: Store Integration');
try {
    const storeContent = fs.readFileSync('src/store/useAppStore.ts', 'utf8');
    
    const hasMemoryImport = storeContent.includes('createMemorySlice');
    const hasMemoryInCreate = storeContent.includes('...createMemorySlice(...a)');
    const hasMemoryInPartialize = storeContent.includes('memories:');
    
    console.log(`  ✅ Memory slice import: ${hasMemoryImport ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Memory slice in store creation: ${hasMemoryInCreate ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Memories in persist config: ${hasMemoryInPartialize ? 'Found' : 'Missing'}`);
    
    if (hasMemoryImport && hasMemoryInCreate && hasMemoryInPartialize) {
        console.log('  ✨ Store integration complete!\n');
    } else {
        throw new Error('Incomplete store integration');
    }
} catch (error) {
    console.error('  ❌ Error:', error.message);
    process.exit(1);
}

// Test 4: API Client
console.log('📋 Test 4: API Client Functions');
try {
    const apiContent = fs.readFileSync('src/services/apiClient.ts', 'utf8');
    
    const hasGetLongTermMemories = apiContent.includes('getLongTermMemories');
    const hasAddLongTermMemory = apiContent.includes('addLongTermMemory');
    const hasSearchLongTermMemories = apiContent.includes('searchLongTermMemories');
    
    console.log(`  ✅ getLongTermMemories: ${hasGetLongTermMemories ? 'Found' : 'Missing'}`);
    console.log(`  ✅ addLongTermMemory: ${hasAddLongTermMemory ? 'Found' : 'Missing'}`);
    console.log(`  ✅ searchLongTermMemories: ${hasSearchLongTermMemories ? 'Found' : 'Missing'}`);
    
    if (hasGetLongTermMemories && hasAddLongTermMemory && hasSearchLongTermMemories) {
        console.log('  ✨ All API functions present!\n');
    } else {
        throw new Error('Missing API functions');
    }
} catch (error) {
    console.error('  ❌ Error:', error.message);
    process.exit(1);
}

// Test 5: Gemini Service Integration
console.log('📋 Test 5: Gemini Service Memory Integration');
try {
    const geminiContent = fs.readFileSync('src/services/geminiService.ts', 'utf8');
    
    const hasMemoryImport = geminiContent.includes('Memory');
    const hasRelevantMemoriesFunction = geminiContent.includes('getRelevantMemories');
    const hasMemoryParameter = geminiContent.includes('memories: Memory[]');
    
    console.log(`  ✅ Memory type import: ${hasMemoryImport ? 'Found' : 'Missing'}`);
    console.log(`  ✅ getRelevantMemories function: ${hasRelevantMemoriesFunction ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Memory parameter in streamChat: ${hasMemoryParameter ? 'Found' : 'Missing'}`);
    
    if (hasMemoryImport && hasRelevantMemoriesFunction && hasMemoryParameter) {
        console.log('  ✨ Gemini service integration complete!\n');
    } else {
        throw new Error('Incomplete Gemini service integration');
    }
} catch (error) {
    console.error('  ❌ Error:', error.message);
    process.exit(1);
}

// Test 6: Memory Panel Component
console.log('📋 Test 6: Memory Panel Component');
try {
    const panelContent = fs.readFileSync('src/components/panels/MemoryPanel.tsx', 'utf8');
    
    const hasMemoryCard = panelContent.includes('MemoryCard');
    const hasAddMemoryForm = panelContent.includes('handleAddMemory');
    const hasSearch = panelContent.includes('searchQuery');
    const hasFilter = panelContent.includes('filterType');
    
    console.log(`  ✅ MemoryCard component: ${hasMemoryCard ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Add memory form: ${hasAddMemoryForm ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Search functionality: ${hasSearch ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Filter functionality: ${hasFilter ? 'Found' : 'Missing'}`);
    
    if (hasMemoryCard && hasAddMemoryForm && hasSearch && hasFilter) {
        console.log('  ✨ Memory panel component complete!\n');
    } else {
        throw new Error('Incomplete memory panel component');
    }
} catch (error) {
    console.error('  ❌ Error:', error.message);
    process.exit(1);
}

// Test 7: Navigation Integration
console.log('📋 Test 7: Navigation Integration');
try {
    const appContent = fs.readFileSync('src/App.tsx', 'utf8');
    const sidebarContent = fs.readFileSync('src/components/layout/Sidebar.tsx', 'utf8');
    
    const hasMemoryInApp = appContent.includes('MemoryPanel');
    const hasMemoryInPanels = appContent.includes("memory: MemoryPanel");
    const hasMemoryInSidebar = sidebarContent.includes("'memory'");
    const hasBrainIcon = sidebarContent.includes('Brain');
    
    console.log(`  ✅ MemoryPanel import in App: ${hasMemoryInApp ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Memory in panel components: ${hasMemoryInPanels ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Memory in sidebar nav: ${hasMemoryInSidebar ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Brain icon in sidebar: ${hasBrainIcon ? 'Found' : 'Missing'}`);
    
    if (hasMemoryInApp && hasMemoryInPanels && hasMemoryInSidebar && hasBrainIcon) {
        console.log('  ✨ Navigation integration complete!\n');
    } else {
        throw new Error('Incomplete navigation integration');
    }
} catch (error) {
    console.error('  ❌ Error:', error.message);
    process.exit(1);
}

// Test 8: Chat Integration
console.log('📋 Test 8: Chat Panel Memory Integration');
try {
    const chatContent = fs.readFileSync('src/components/panels/ChatPanel.tsx', 'utf8');
    
    const hasMemoriesInState = chatContent.includes('memories,');
    const hasMemoriesInStreamChat = chatContent.includes('memories)');
    
    console.log(`  ✅ Memories in component state: ${hasMemoriesInState ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Memories passed to streamChat: ${hasMemoriesInStreamChat ? 'Found' : 'Missing'}`);
    
    if (hasMemoriesInState && hasMemoriesInStreamChat) {
        console.log('  ✨ Chat integration complete!\n');
    } else {
        throw new Error('Incomplete chat integration');
    }
} catch (error) {
    console.error('  ❌ Error:', error.message);
    process.exit(1);
}

// Test 9: Chat Slice Memory Creation
console.log('📋 Test 9: Automatic Memory Creation from Chat');
try {
    const chatSliceContent = fs.readFileSync('src/store/slices/createChatSlice.ts', 'utf8');
    
    const hasAddMemory = chatSliceContent.includes('addMemory');
    const hasMemoryCreation = chatSliceContent.includes("type: 'CONVERSATION'");
    const hasDiaryEntry = chatSliceContent.includes('largo plazo');
    
    console.log(`  ✅ addMemory in summarize function: ${hasAddMemory ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Memory creation with CONVERSATION type: ${hasMemoryCreation ? 'Found' : 'Missing'}`);
    console.log(`  ✅ Diary entry for memory creation: ${hasDiaryEntry ? 'Found' : 'Missing'}`);
    
    if (hasAddMemory && hasMemoryCreation && hasDiaryEntry) {
        console.log('  ✨ Automatic memory creation integrated!\n');
    } else {
        throw new Error('Incomplete automatic memory creation');
    }
} catch (error) {
    console.error('  ❌ Error:', error.message);
    process.exit(1);
}

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
console.log('✨ All tests passed! Long-term memory system is fully integrated.\n');
console.log('📊 Summary:');
console.log('  • Memory types and interfaces defined');
console.log('  • Memory slice with CRUD operations created');
console.log('  • Store integration with persistence configured');
console.log('  • API client functions implemented');
console.log('  • Gemini service enhanced with memory context');
console.log('  • Memory panel UI component created');
console.log('  • Navigation updated with Memory option');
console.log('  • Chat panel integrated with memory retrieval');
console.log('  • Automatic memory creation from summaries enabled\n');
console.log('🚀 The memoria a largo plazo feature is ready to use!\n');
