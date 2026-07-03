import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

function ChatPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [listening, setListening] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const newMessage = { role: 'user', content: input };
    setMessages([...messages, newMessage]);

    try {
      const response = await axios.post(`${API_BASE}/chat/message`, {
        message: input
      });

      const botMessage = {
        role: 'companion',
        content: response.data.response
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Chat error:', error);
    }

    setInput('');
  };

  const startVoiceInput = () => {
    if (!('webkitSpeechRecognition' in window)) {
      alert('Speech Recognition not supported');
      return;
    }

    const recognition = new webkitSpeechRecognition();
    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(result => result[0].transcript)
        .join('');
      setInput(transcript);
    };

    recognition.start();
  };

  return (
    <div className="chat-panel">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <p>{msg.content}</p>
          </div>
        ))}
      </div>

      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Talk to Kai..."
        />
        <button onClick={handleSend}>Send</button>
        <button
          className={listening ? 'listening' : ''}
          onClick={startVoiceInput}
        >
          🎤
        </button>
      </div>
    </div>
  );
}

export default ChatPanel;
