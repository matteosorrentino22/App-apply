import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'

const ToastContext = createContext(null)

let nextId = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timers = useRef(new Map())

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
    const timer = timers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
  }, [])

  // `action` opzionale ({ label, onClick }) per il caso "undo" (Sprint 19):
  // il toast resta visibile pochi secondi, cliccando l'azione la annulla
  // prima dello scadere.
  const showToast = useCallback(
    (message, { action, duration = 5000 } = {}) => {
      const id = ++nextId
      setToasts((current) => [...current, { id, message, action }])
      const timer = setTimeout(() => dismiss(id), duration)
      timers.current.set(id, timer)
      return id
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={{ showToast, dismiss }}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className="pointer-events-auto flex items-center gap-3 rounded-lg border border-border bg-card px-4 py-2.5 text-sm text-foreground shadow-md"
          >
            <span>{toast.message}</span>
            {toast.action && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  toast.action.onClick()
                  dismiss(toast.id)
                }}
                className="text-primary"
              >
                {toast.action.label}
              </Button>
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast va usato dentro <ToastProvider>')
  }
  return context
}
