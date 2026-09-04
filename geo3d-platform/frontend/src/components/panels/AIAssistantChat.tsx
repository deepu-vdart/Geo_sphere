import React, { useState, useRef, useEffect } from 'react'
import { useViewerStore, useAppStore } from '../../stores'
import { api } from '../../api/client'

export default function AIAssistantChat() {
  const {
    aiDrawerOpen,
    setAiDrawerOpen,
    aiChatMessages,
    addAiChatMessage,
    clearAiChat,
    setFlyToTarget,
    setAiMarkerPin,
    setActiveTool,
    setPointCloudColorMode,
    toggleClassFilter,
  } = useViewerStore()

  const activeDataset = useAppStore((s) => s.activeDataset)
  const [inputQuery, setInputQuery] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [aiChatMessages, isTyping])

  if (!aiDrawerOpen) return null

  const handleSend = async (queryText: string) => {
    const text = queryText.trim()
    if (!text || isTyping || !activeDataset) return

    setInputQuery('')
    addAiChatMessage({ role: 'user', content: text })
    setIsTyping(true)

    try {
      const res = await api.chatWithAI(activeDataset.id, text)
      const data = res.data

      addAiChatMessage({
        role: 'assistant',
        content: data.reply,
        toolCalled: data.tool_called,
        action: data.action,
      })

      // Dispatch CesiumJS actions if returned
      if (data.action) {
        if (data.action.type === 'fly_to' && data.action.coords) {
          setFlyToTarget(data.action.coords)
          if (data.action.pin) {
            setAiMarkerPin(data.action.pin)
          }
        } else if (data.action.type === 'filter_classes' && data.action.classes) {
          // Disable all except target classes
          const targetSet = new Set<number>(data.action.classes)
          for (let i = 0; i <= 15; i++) {
            const shouldShow = targetSet.has(i)
            const currentShow = useViewerStore.getState().activeClassFilters[i] !== false
            if (shouldShow !== currentShow) {
              toggleClassFilter(i)
            }
          }
          if (data.action.color_mode) {
            setPointCloudColorMode(data.action.color_mode)
          }
        } else if (data.action.type === 'activate_tool' && data.action.tool) {
          setActiveTool(data.action.tool)
        } else if (data.action.type === 'set_color_mode' && data.action.mode) {
          setPointCloudColorMode(data.action.mode)
        }
      }
    } catch (err: any) {
      addAiChatMessage({
        role: 'assistant',
        content: `⚠️ Failed to execute query: ${err?.response?.data?.detail || err?.message || 'Server error'}`,
      })
    } finally {
      setIsTyping(false)
    }
  }

  const promptChips = [
    'Fly to highest elevation point',
    'Show only buildings',
    'Is this terrain suitable for building?',
    'Bare earth ground mode',
    'Measure volume & cut-fill',
  ]

  return (
    <div
      className="ai-chat-drawer"
      style={{
        position: 'absolute',
        top: 60,
        right: 320,
        width: 380,
        height: 520,
        backgroundColor: '#111726',
        borderRadius: 10,
        boxShadow: '0 20px 40px rgba(0,0,0,0.6), 0 0 0 1px rgba(56, 189, 248, 0.25)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 50,
        backdropFilter: 'blur(12px)',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 14px',
          background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(15, 23, 42, 0.95))',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 6,
              background: 'linear-gradient(135deg, #38bdf8, #818cf8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 14,
            }}
          >
            🤖
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#f1f5f9' }}>
              AI Geospatial Assistant
            </div>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>
              Grounded in active survey metrics
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <button
            onClick={clearAiChat}
            title="Clear Chat"
            style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 11 }}
          >
            Clear
          </button>
          <button
            onClick={() => setAiDrawerOpen(false)}
            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: 14, padding: '0 4px' }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Messages list */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 12,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        {aiChatMessages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '86%',
              backgroundColor: msg.role === 'user' ? '#0284c7' : '#1e293b',
              color: '#f8fafc',
              padding: '8px 12px',
              borderRadius: 8,
              fontSize: 11.5,
              lineHeight: 1.45,
              border: msg.role === 'user' ? 'none' : '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
            {msg.toolCalled && (
              <div
                style={{
                  marginTop: 6,
                  padding: '2px 6px',
                  borderRadius: 4,
                  fontSize: 9,
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  display: 'inline-block',
                }}
              >
                ⚡ Action executed: {msg.toolCalled}
              </div>
            )}
          </div>
        ))}
        {isTyping && (
          <div
            style={{
              alignSelf: 'flex-start',
              backgroundColor: '#1e293b',
              padding: '8px 12px',
              borderRadius: 8,
              fontSize: 11,
              color: '#94a3b8',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <div className="scene-loading__spinner" style={{ width: 10, height: 10, borderWidth: 2 }} />
            Analyzing spatial dataset…
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Chips */}
      <div
        style={{
          padding: '6px 10px',
          display: 'flex',
          gap: 4,
          overflowX: 'auto',
          borderTop: '1px solid rgba(255,255,255,0.05)',
          background: 'rgba(15, 23, 42, 0.4)',
        }}
      >
        {promptChips.map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(chip)}
            style={{
              flexShrink: 0,
              fontSize: 9.5,
              padding: '3px 8px',
              borderRadius: 12,
              background: 'rgba(56, 189, 248, 0.1)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              color: '#38bdf8',
              cursor: 'pointer',
            }}
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Input row */}
      <div
        style={{
          padding: '10px 12px',
          borderTop: '1px solid rgba(255,255,255,0.08)',
          display: 'flex',
          gap: 6,
          background: '#0f172a',
        }}
      >
        <input
          type="text"
          placeholder={activeDataset ? "Ask about elevation, slopes, buildings..." : "Select a dataset first"}
          disabled={!activeDataset || isTyping}
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend(inputQuery)}
          style={{
            flex: 1,
            backgroundColor: '#1e293b',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 6,
            padding: '7px 10px',
            fontSize: 11,
            color: '#f8fafc',
            outline: 'none',
          }}
        />
        <button
          onClick={() => handleSend(inputQuery)}
          disabled={!inputQuery.trim() || isTyping || !activeDataset}
          className="btn btn--primary btn--sm"
          style={{ padding: '0 12px', fontSize: 11 }}
        >
          Send
        </button>
      </div>
    </div>
  )
}
