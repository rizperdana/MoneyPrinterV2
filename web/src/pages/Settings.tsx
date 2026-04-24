import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Settings as SettingsIcon, Eye, EyeOff, Save } from "lucide-react"
import { toast } from "sonner"

function ApiKeyField({
  label,
  name,
  value,
  onChange,
}: {
  label: string
  name: string
  value: string
  onChange: (name: string, val: string) => void
}) {
  const [visible, setVisible] = useState(false)

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex gap-2">
        <Input
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(name, e.target.value)}
          placeholder="Enter API key..."
        />
        <Button
          variant="outline"
          size="icon"
          onClick={() => setVisible(!visible)}
          type="button"
        >
          {visible ? (
            <EyeOff className="w-4 h-4" />
          ) : (
            <Eye className="w-4 h-4" />
          )}
        </Button>
      </div>
    </div>
  )
}

interface ModelConfig {
  display_name: string
  available_models: string[]
  fallback_chain: string[]
  primary_model: string
}

export default function Settings() {
  const [config, setConfig] = useState<Record<string, unknown>>({})
  const [modelRouting, setModelRouting] = useState<Record<string, ModelConfig>>({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.settings.get().then(setConfig).catch(() => {})
    api.settings.getModels().then(setModelRouting).catch(() => {})
  }, [])

  const updateField = (name: string, value: unknown) => {
    setConfig((prev) => ({ ...prev, [name]: value }))
  }

  const handleModelChange = (job: string, model: string) => {
    setConfig((prev) => ({ ...prev, [`model_${job}`]: model }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      // Include model selections and fallback chains
      const updates: Record<string, unknown> = {}
      const editableFields = [
        "llm_base_url",
        "llm_model",
        "tts_voice",
        "headless",
        "firefox_profile",
        "imagemagick_path",
        "is_for_kids",
        "threads",
        "verbose",
        "script_sentence_length",
        "languagevoices",
      ]
      // Add model selections and fallback chains
      for (const job of Object.keys(modelRouting)) {
        editableFields.push(`model_${job}`)
        editableFields.push(`model_${job}_fallback`)
      }
      
      // Log editableFields to see what's being checked
      console.log("All editable fields:", editableFields)
      
      // Collect all updates including model settings
      console.log("Config before save:", JSON.stringify(config, null, 2))
      
      // Debug what's in config vs what we expect
      const allModelKeys = []
      for (const job of Object.keys(modelRouting)) {
        allModelKeys.push(`model_${job}`)
        allModelKeys.push(`model_${job}_fallback`)
      }
      console.log("Looking for these model keys:", allModelKeys)
      console.log("Which exist in config?:", allModelKeys.map(k => ({key: k, exists: k in config, value: config[k]})))
      
      for (const key of editableFields) {
        if (key in config) {
          updates[key] = config[key]
        }
      }
      console.log("Saving updates:", JSON.stringify(updates, null, 2))
      
      // Debug: log API response
      const response = await api.settings.put(updates)
      console.log("API response:", response)
      
      toast.success("Settings saved")
    } catch (err) {
      toast.error("Failed to save settings")
      console.error(err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
          <SettingsIcon className="w-4 h-4 text-white" />
        </div>
        <h1 className="text-xl font-semibold">Settings</h1>
      </div>

      <div className="space-y-8 max-w-2xl">
        {/* API Keys */}
        <div>
          <h2 className="text-lg font-semibold mb-4">API Keys</h2>
          <Card>
            <CardContent className="space-y-4 pt-6">
              <ApiKeyField
                label="Cliproxy API Key (LLM)"
                name="CLIPROXY_API_KEY"
                value={String(config.CLIPROXY_API_KEY || "")}
                onChange={updateField}
              />
            </CardContent>
          </Card>
        </div>

        <Separator />

        {/* LLM Model Routing */}
        <div>
          <h2 className="text-lg font-semibold mb-4">LLM Model Selection</h2>
          <Card>
            <CardContent className="space-y-6 pt-6">
              {Object.entries(modelRouting).map(([job, cfg]) => (
                <div key={job} className="space-y-3 border-b pb-4 last:border-0">
                  <Label className="font-medium">{cfg.display_name}</Label>
                  
                  {/* Primary model dropdown */}
                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground">Primary Model</span>
                    <select
                      value={String(config[`model_${job}`] || cfg.primary_model)}
                      onChange={(e) => handleModelChange(job, e.target.value)}
                      className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                    >
                      {cfg.available_models.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </div>

                    {/* Fallback chain */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">Fallback Chain (in order)</span>
                        <button
                          type="button"
                          onClick={() => {
                            const chainKey = `model_${job}_fallback`
                            const available = cfg.available_models || []
                            const current = (config[chainKey] as string[]) || cfg.fallback_chain || []
                            const unused = available.filter((m: string) => !current.includes(m))
                            if (unused.length > 0) {
                              console.log(`Adding to ${chainKey}:`, [...current, unused[0]])
                              setConfig((prev) => ({
                                ...prev,
                                [chainKey]: [...current, unused[0]],
                              }))
                            }
                          }}
                          className="text-xs text-primary hover:text-primary/80"
                        >
                          + Add Model
                        </button>
                      </div>
                      <div className="space-y-1">
                        {/* Use config value directly for rendering so UI updates on change */}
                        {((config[`model_${job}_fallback`] as string[]) || cfg.fallback_chain || []).map((model: string, idx: number) => {
                        const chainKey = `model_${job}_fallback`
                        const currentChain = (config[chainKey] as string[]) || cfg.fallback_chain || []
                        return (
                        <div key={`${job}-${idx}`} className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground w-4">{idx + 1}.</span>
                          <select
                            value={currentChain[idx] || model}
                            onChange={(e) => {
                              const newChain = [...currentChain]
                              newChain[idx] = e.target.value
                              console.log(`Updating ${chainKey}:`, newChain)
                              setConfig((prev) => ({
                                ...prev,
                                [chainKey]: newChain,
                              }))
                            }}
                            className="flex-1 text-sm border rounded px-2 py-1"
                          >
                            {(cfg.available_models || []).map((m: string) => (
                              <option key={m} value={m}>{m}</option>
                            ))}
                          </select>
                          <button
                            type="button"
                            onClick={() => {
                              const chainKey = `model_${job}_fallback`
                              const currentChain = [...((config[chainKey] as string[]) || cfg.fallback_chain || [])]
                              if (idx === 0 || currentChain.length < 2) return
                              ;[currentChain[idx - 1], currentChain[idx]] = [currentChain[idx], currentChain[idx - 1]]
                              console.log(`Moving up ${chainKey}:`, currentChain)
                              setConfig((prev) => ({
                                ...prev,
                                [chainKey]: currentChain,
                              }))
                            }}
                            disabled={idx === 0}
                            className={`text-xs px-2 py-1 rounded ${idx === 0 ? 'text-muted-foreground/30 cursor-not-allowed' : 'text-muted-foreground hover:text-foreground bg-secondary'}`}
                          >
                            ↑
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const chainKey = `model_${job}_fallback`
                              const currentChain = [...((config[chainKey] as string[]) || cfg.fallback_chain || [])]
                              if (idx >= currentChain.length - 1) return
                              ;[currentChain[idx], currentChain[idx + 1]] = [currentChain[idx + 1], currentChain[idx]]
                              console.log(`Moving down ${chainKey}:`, currentChain)
                              setConfig((prev) => ({
                                ...prev,
                                [chainKey]: currentChain,
                              }))
                            }}
                            disabled={idx >= (cfg.fallback_chain || []).length - 1}
                            className={`text-xs px-2 py-1 rounded ${idx >= (cfg.fallback_chain || []).length - 1 ? 'text-muted-foreground/30 cursor-not-allowed' : 'text-muted-foreground hover:text-foreground bg-secondary'}`}
                          >
                            ↓
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const chainKey = `model_${job}_fallback`
                              const currentChain = [...((config[chainKey] as string[]) || cfg.fallback_chain || [])]
                              const newChain = currentChain.filter((_: string, i: number) => i !== idx)
                              console.log(`Deleting from ${chainKey}:`, newChain)
                              setConfig((prev) => ({
                                ...prev,
                                [chainKey]: newChain,
                              }))
                            }}
                            className="text-xs px-2 py-1 rounded text-red-500 hover:text-red-400 bg-secondary"
                          >
                            ✕
                          </button>
                        </div>
                        )})}
                      </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <Separator />

        {/* LLM Base URL (legacy) */}
        <div>
          <h2 className="text-lg font-semibold mb-4">LLM Connection</h2>
          <Card>
            <CardContent className="space-y-4 pt-6">
              <div className="space-y-2">
                <Label>LLM Base URL</Label>
                <Input
                  value={String(config.llm_base_url || "")}
                  onChange={(e) => updateField("llm_base_url", e.target.value)}
                  placeholder="http://localhost:8317/v1"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        <Separator />

        {/* Defaults */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Generation Defaults</h2>
          <Card>
            <CardContent className="space-y-4 pt-6">
              {/* TTS Voice Section — Per-Language */}
              <div className="space-y-4">
                <Label>TTS Voices by Language</Label>
                <p className="text-xs text-muted-foreground">
                  Configure the voice used for each language. Indonesian voices: id-ID-GadisNeural (F), id-ID-ArdiNeural (M).
                </p>

                {/* Default voice */}
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">Default (English)</span>
                  <select
                    value={String(config.tts_voice || "en-US-JennyNeural")}
                    onChange={(e) => updateField("tts_voice", e.target.value)}
                    className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                  >
                    <option value="en-US-JennyNeural">en-US-JennyNeural (Female)</option>
                    <option value="en-US-GuyNeural">en-US-GuyNeural (Male)</option>
                    <option value="en-US-StefanNeural">en-US-StefanNeural (Male)</option>
                    <option value="en-GB-SoniaNeural">en-GB-SoniaNeural (Female)</option>
                    <option value="en-GB-RyanNeural">en-GB-RyanNeural (Male)</option>
                  </select>
                </div>

                {/* Indonesian voices */}
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">Indonesian</span>
                  <select
                    value={String(
                      (() => {
                        try {
                          const lv = typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : config.languagevoices;
                          return lv?.Indonesian || "id-ID-GadisNeural";
                        } catch { return "id-ID-GadisNeural"; }
                      })()
                    )}
                    onChange={(e) => {
                      const lv = (() => {
                        try {
                          return typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : (config.languagevoices || {});
                        } catch { return {}; }
                      })();
                      lv["Indonesian"] = e.target.value;
                      updateField("languagevoices", lv);
                    }}
                    className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                  >
                    <option value="id-ID-GadisNeural">id-ID-GadisNeural (Female — Friendly, Positive)</option>
                    <option value="id-ID-ArdiNeural">id-ID-ArdiNeural (Male — Friendly, Positive)</option>
                  </select>
                </div>

                {/* Malay voices */}
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">Malay</span>
                  <select
                    value={String(
                      (() => {
                        try {
                          const lv = typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : config.languagevoices;
                          return lv?.Malay || "ms-MY-OsmanNeural";
                        } catch { return "ms-MY-OsmanNeural"; }
                      })()
                    )}
                    onChange={(e) => {
                      const lv = (() => {
                        try {
                          return typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : (config.languagevoices || {});
                        } catch { return {}; }
                      })();
                      lv["Malay"] = e.target.value;
                      updateField("languagevoices", lv);
                    }}
                    className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                  >
                    <option value="ms-MY-OsmanNeural">ms-MY-OsmanNeural (Male)</option>
                    <option value="ms-MY-YasminNeural">ms-MY-YasminNeural (Female)</option>
                  </select>
                </div>

                {/* Javanese voices */}
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">Javanese</span>
                  <select
                    value={String(
                      (() => {
                        try {
                          const lv = typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : config.languagevoices;
                          return lv?.Javanese || "jv-ID-DimasNeural";
                        } catch { return "jv-ID-DimasNeural"; }
                      })()
                    )}
                    onChange={(e) => {
                      const lv = (() => {
                        try {
                          return typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : (config.languagevoices || {});
                        } catch { return {}; }
                      })();
                      lv["Javanese"] = e.target.value;
                      updateField("languagevoices", lv);
                    }}
                    className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                  >
                    <option value="jv-ID-DimasNeural">jv-ID-DimasNeural (Male)</option>
                    <option value="jv-ID-SitiNeural">jv-ID-SitiNeural (Female)</option>
                  </select>
                </div>

                {/* Sundanese voices */}
                <div className="space-y-1">
                  <span className="text-xs text-muted-foreground">Sundanese</span>
                  <select
                    value={String(
                      (() => {
                        try {
                          const lv = typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : config.languagevoices;
                          return lv?.Sundanese || "su-ID-JajangNeural";
                        } catch { return "su-ID-JajangNeural"; }
                      })()
                    )}
                    onChange={(e) => {
                      const lv = (() => {
                        try {
                          return typeof config.languagevoices === 'string' ? JSON.parse(config.languagevoices) : (config.languagevoices || {});
                        } catch { return {}; }
                      })();
                      lv["Sundanese"] = e.target.value;
                      updateField("languagevoices", lv);
                    }}
                    className="w-full px-3 py-2 border rounded-md bg-background text-sm"
                  >
                    <option value="su-ID-JajangNeural">su-ID-JajangNeural (Male)</option>
                    <option value="su-ID-TutiNeural">su-ID-TutiNeural (Female)</option>
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Script Sentence Length</Label>
                <Input
                  type="number"
                  value={String(config.script_sentence_length || 4)}
                  onChange={(e) =>
                    updateField("script_sentence_length", parseInt(e.target.value) || 4)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>Threads</Label>
                <Input
                  type="number"
                  value={String(config.threads || 2)}
                  onChange={(e) =>
                    updateField("threads", parseInt(e.target.value) || 2)
                  }
                />
              </div>
              <div className="flex items-center gap-3">
                <Switch
                  checked={!!config.headless}
                  onCheckedChange={(v) => updateField("headless", v)}
                />
                <Label>Headless Browser</Label>
              </div>
              <div className="flex items-center gap-3">
                <Switch
                  checked={!!config.is_for_kids}
                  onCheckedChange={(v) => updateField("is_for_kids", v)}
                />
                <Label>For Kids</Label>
              </div>
              <div className="flex items-center gap-3">
                <Switch
                  checked={!!config.verbose}
                  onCheckedChange={(v) => updateField("verbose", v)}
                />
                <Label>Verbose Logging</Label>
              </div>
            </CardContent>
          </Card>
        </div>

        <Separator />

        {/* Paths */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Paths</h2>
          <Card>
            <CardContent className="space-y-4 pt-6">
              <div className="space-y-2">
                <Label>Firefox Profile</Label>
                <Input
                  value={String(config.FIREFOX_PROFILE || config.firefox_profile || "")}
                  onChange={(e) => updateField("firefox_profile", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>ImageMagick Path</Label>
                <Input
                  value={String(config.imagemagick_path || "")}
                  onChange={(e) => updateField("imagemagick_path", e.target.value)}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        <Button onClick={handleSave} disabled={saving} className="w-full">
          <Save className="w-4 h-4 mr-2" />
          {saving ? "Saving..." : "Save Settings"}
        </Button>
      </div>
    </div>
  )
}
