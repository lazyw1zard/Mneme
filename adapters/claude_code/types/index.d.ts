// Session state of the receptor ($.state): survives a reload of the mod, resets with /clear.
declare module 'claude-code' {
  interface PluginState {
    'mneme-receptor': {
      // the surface now in the agent's context; null = the context does not have it
      shown: string | null
      // read model mtime the last build saw
      builtMtime: number | null
      // why the context lost the surface ('compact' | 'clear'), until the next delivery
      resetReason: string | null
      // what the last build found
      status: { state: string; at: string | null; topics: number; reason: string | null; error: string | null }
      // dev: every delivery in this session, oldest first
      history: { at: string; why: string; text: string; topics: number }[]
    }
  }
}
