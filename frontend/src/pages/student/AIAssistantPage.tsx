import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import BookSummarizer from '../../components/BookSummarizer';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import {
  Bot, Send, Sparkles, BookOpen, Brain, RefreshCw,
  Copy, Check, User, ChevronRight, HelpCircle
} from 'lucide-react';

interface Message {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
}

export default function AIAssistantPage() {
  const [params, setParams] = useSearchParams();
  const summarizing = params.get('tab') === 'summarize';
  const selectTab = (summary: boolean) => setParams(summary ? { tab: 'summarize' } : {});
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'ai',
      text: `Hello ${user?.name ? user.name.split(' ')[0] : 'there'}! 👋 I'm your Book Bridge AI Study Assistant. I can help you find books in the campus library, summarize complex engineering concepts, generate study roadmaps, or answer questions about your courses. How can I assist your learning today?`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const suggestedPrompts = [
    { label: 'Python Recommendations', prompt: 'What are the best books in the library to learn Python from scratch?' },
    { label: 'DSA Roadmap', prompt: 'Create a step-by-step learning path for Data Structures and Algorithms.' },
    { label: 'Summarize a chapter', prompt: 'Open Book Summarizer to paste text or upload a PDF / TXT file.' },
    { label: 'Find Book by Shelf', prompt: 'Where is Operating System Concepts located in the library?' },
  ];

  const handleSend = async (textToSend?: string) => {
    const queryText = textToSend || input;
    if (!queryText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!textToSend) setInput('');
    setIsLoading(true);

    try {
      const res = await api.post('/ai/chat', { query: queryText });
      const aiReply = res.data?.response || "I couldn't find a direct answer, but please check the library catalog!";
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: aiReply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: "I'm having trouble connecting to the library AI service right now. Please try again in a moment.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6 flex flex-wrap gap-2" aria-label="AI tools">
        <button onClick={() => selectTab(false)} aria-pressed={!summarizing} className={`rounded-xl px-4 py-2.5 text-sm font-semibold ${!summarizing ? 'bg-blue-600 text-white' : 'bg-[#111827] text-gray-400'}`}>Library Assistant</button>
        <button onClick={() => selectTab(true)} aria-pressed={summarizing} className={`rounded-xl px-4 py-2.5 text-sm font-semibold ${summarizing ? 'bg-blue-600 text-white' : 'bg-[#111827] text-gray-400'}`}>Book Summarizer</button>
      </div>
      <div hidden={!summarizing}><BookSummarizer /></div>
      <div hidden={summarizing}>
    <div className="space-y-6 pb-12 flex flex-col min-h-[600px] h-[calc(100vh-180px)]">
      {/* Header */}
      <div className="bg-[#111827]/80 backdrop-blur-md border border-gray-800/80 rounded-2xl p-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400 shadow-[0_0_12px_rgba(59,130,246,0.3)]">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              Book Bridge AI Assistant <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-medium">Online</span>
            </h1>
            <p className="text-xs text-gray-400">Library knowledge base • Textbook locator • Study companion</p>
          </div>
        </div>

        <button
          onClick={() => setMessages([messages[0]])}
          className="text-xs text-gray-400 hover:text-white bg-[#172033] hover:bg-gray-800 border border-gray-800 px-3 py-1.5 rounded-xl transition flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Clear Chat
        </button>
      </div>

      {/* Suggested Prompts Grid (only shown if 1-2 messages) */}
      {messages.length <= 2 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {suggestedPrompts.map((item, idx) => (
            <button
              key={idx}
              onClick={() => idx === 2 ? selectTab(true) : handleSend(item.prompt)}
              className="text-left p-3 rounded-xl bg-[#111827]/60 hover:bg-[#172033] border border-gray-800/80 hover:border-blue-500/30 transition group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-blue-400 group-hover:text-blue-300">{item.label}</span>
                <ChevronRight className="w-3.5 h-3.5 text-gray-500 group-hover:text-white transition" />
              </div>
              <p className="text-[11px] text-gray-400 mt-1 line-clamp-1">{item.prompt}</p>
            </button>
          ))}
        </div>
      )}

      {/* Messages Thread Container */}
      <div className="flex-1 overflow-y-auto bg-[#111827]/60 backdrop-blur-md border border-gray-800/80 rounded-2xl p-5 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start gap-3 ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}
          >
            {/* Avatar */}
            <div
              className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center text-xs font-bold ${
                msg.sender === 'user'
                  ? 'bg-gradient-to-br from-blue-500 to-purple-600 text-white'
                  : 'bg-blue-600/20 border border-blue-500/30 text-blue-400'
              }`}
            >
              {msg.sender === 'user' ? user?.name?.charAt(0) || 'U' : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[75%] rounded-2xl p-4 text-xs leading-relaxed relative group ${
                msg.sender === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-none'
                  : 'bg-[#172033] border border-gray-800 text-gray-200 rounded-tl-none shadow-md'
              }`}
            >
              <div className="whitespace-pre-line">{msg.text}</div>
              <div
                className={`text-[10px] mt-2 flex items-center justify-between gap-4 ${
                  msg.sender === 'user' ? 'text-blue-200' : 'text-gray-500'
                }`}
              >
                <span>{msg.timestamp}</span>
                {msg.sender === 'ai' && (
                  <button
                    onClick={() => handleCopy(msg.id, msg.text)}
                    className="opacity-0 group-hover:opacity-100 transition hover:text-gray-300"
                    title="Copy response"
                  >
                    {copiedId === msg.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-xl bg-blue-600/20 border border-blue-500/30 text-blue-400 flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-[#172033] border border-gray-800 rounded-2xl rounded-tl-none p-4 flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" />
              <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce [animation-delay:0.2s]" />
              <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce [animation-delay:0.4s]" />
            </div>
          </div>
        )}
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="relative"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about library books, exam syllabus, programming concepts..."
          className="w-full bg-[#111827] border border-gray-700/60 rounded-2xl pl-5 pr-14 py-3.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 shadow-xl"
        />
        <button
          type="submit"
          aria-label="Send message"
          disabled={!input.trim() || isLoading}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 w-9 h-9 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-800 disabled:text-gray-600 rounded-xl flex items-center justify-center text-white transition shadow-[0_0_10px_rgba(37,99,235,0.4)]"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
    </div>
    </div>
  );
}
