interface GPTConfigSectionProps {
  gptModel: string;
  setGptModel: (model: string) => void;
  gptApiKey: string;
  setGptApiKey: (key: string) => void;
  useEnvKey: boolean;
  setUseEnvKey: (use: boolean) => void;
  gptEndpoint: string;
  setGptEndpoint: (endpoint: string) => void;
}

export default function GPTConfigSection({
  gptModel, setGptModel, gptApiKey, setGptApiKey,
  useEnvKey, setUseEnvKey, gptEndpoint, setGptEndpoint
}: GPTConfigSectionProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">GPT Model</label>
        <select
          value={gptModel}
          onChange={(e) => setGptModel(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md"
        >
          <option value="gpt-4">GPT-4</option>
          <option value="gpt-4-turbo">GPT-4 Turbo</option>
          <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
        </select>
      </div>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1">
          <input
            type="checkbox"
            checked={useEnvKey}
            onChange={(e) => setUseEnvKey(e.target.checked)}
            className="rounded border-gray-300"
          />
          Use server environment API key
        </label>
      </div>

      {!useEnvKey && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">OpenAI API Key</label>
          <input
            type="password"
            value={gptApiKey}
            onChange={(e) => setGptApiKey(e.target.value)}
            placeholder="sk-..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          />
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Custom Endpoint (optional)</label>
        <input
          type="text"
          value={gptEndpoint}
          onChange={(e) => setGptEndpoint(e.target.value)}
          placeholder="https://api.openai.com/v1"
          className="w-full px-3 py-2 border border-gray-300 rounded-md"
        />
      </div>
    </div>
  );
}
