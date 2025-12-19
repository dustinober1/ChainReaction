"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";

export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
    queryResults?: any;
}

interface ChatInterfaceProps {
    messages: ChatMessage[];
    onSendMessage: (message: string) => void;
    isLoading?: boolean;
    onResultClick?: (result: any) => void;
}

export default function ChatInterface({
    messages,
    onSendMessage,
    isLoading = false,
    onResultClick,
}: ChatInterfaceProps) {
    const [input, setInput] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Auto-resize textarea
    useEffect(() => {
        if (inputRef.current) {
            inputRef.current.style.height = "auto";
            inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
        }
    }, [input]);

    const handleSubmit = () => {
        if (input.trim() && !isLoading) {
            onSendMessage(input.trim());
            setInput("");
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const formatTime = (date: Date) => {
        return date.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    return (
        <div className="flex flex-col h-full glass-card">
            {/* Header */}
            <div className="px-4 py-3 border-b border-white/10">
                <h2 className="text-lg font-semibold gradient-text">Risk Analyst</h2>
                <p className="text-xs text-gray-400">Ask questions about your supply chain</p>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && (
                    <div className="text-center text-gray-500 py-8">
                        <svg
                            className="w-12 h-12 mx-auto mb-4 text-gray-600"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={1.5}
                                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                            />
                        </svg>
                        <p className="text-sm">Start a conversation to analyze risks</p>
                        <div className="mt-4 space-y-2">
                            <SuggestedQuery onClick={onSendMessage}>
                                What products are affected by the Taiwan typhoon?
                            </SuggestedQuery>
                            <SuggestedQuery onClick={onSendMessage}>
                                Show me single-source components
                            </SuggestedQuery>
                            <SuggestedQuery onClick={onSendMessage}>
                                What&apos;s the overall supply chain risk?
                            </SuggestedQuery>
                        </div>
                    </div>
                )}

                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex ${message.role === "user" ? "justify-end" : "justify-start"
                            }`}
                    >
                        <div
                            className={`max-w-[85%] rounded-2xl px-4 py-2 ${message.role === "user"
                                    ? "bg-blue-600 text-white"
                                    : "bg-gray-800 text-gray-100 border border-white/5"
                                }`}
                        >
                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                            {/* Query Results */}
                            {message.queryResults && (
                                <div className="mt-3 space-y-2">
                                    {message.queryResults.affectedProducts?.map((product: any) => (
                                        <button
                                            key={product.id}
                                            onClick={() => onResultClick?.(product)}
                                            className="w-full text-left px-3 py-2 bg-white/5 rounded-lg hover:bg-white/10 transition"
                                        >
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm font-medium">{product.name}</span>
                                                <span
                                                    className={`text-xs px-2 py-0.5 rounded-full ${product.riskScore > 70
                                                            ? "bg-red-500/20 text-red-400"
                                                            : product.riskScore > 40
                                                                ? "bg-amber-500/20 text-amber-400"
                                                                : "bg-green-500/20 text-green-400"
                                                        }`}
                                                >
                                                    {product.riskScore}%
                                                </span>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}

                            <p className="text-xs mt-1 opacity-50">{formatTime(message.timestamp)}</p>
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex justify-start">
                        <div className="bg-gray-800 rounded-2xl px-4 py-3 border border-white/5">
                            <div className="flex space-x-2">
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" />
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-100" />
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-200" />
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-white/10">
                <div className="flex items-end gap-2">
                    <textarea
                        ref={inputRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask about supply chain risks..."
                        className="flex-1 bg-gray-800/50 border border-white/10 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 placeholder-gray-500"
                        rows={1}
                        disabled={isLoading}
                    />
                    <button
                        onClick={handleSubmit}
                        disabled={!input.trim() || isLoading}
                        className="p-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-xl transition-colors"
                    >
                        <svg
                            className="w-5 h-5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                            />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}

function SuggestedQuery({
    children,
    onClick,
}: {
    children: string;
    onClick: (query: string) => void;
}) {
    return (
        <button
            onClick={() => onClick(children)}
            className="block w-full text-left px-3 py-2 text-xs text-gray-400 bg-gray-800/50 hover:bg-gray-800 rounded-lg transition"
        >
            → {children}
        </button>
    );
}
