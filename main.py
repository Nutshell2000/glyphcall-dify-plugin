from dify_plugin import DifyPluginEnv, Plugin

# Scanned documents are read by OCR and can take a while; the API itself answers within 60 seconds.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=180))

if __name__ == "__main__":
    plugin.run()
