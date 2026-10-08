class ShopClaimGuiConfig
{
	string theme_prefix;

	void ShopClaimGuiConfig()
	{
		theme_prefix = "ShopClaimTheme";
	}
};

class ShopClaimModConfig
{
	string bridge_url;
	string server_id;
	string api_token;
	int shop_server_id;
	int wargm_server_id;
	string claim_command;
	bool enable_chat_commands;
	string container_class;
	int container_empty_check_sec;
	int abandoned_container_hours;
	int vehicle_spawn_cooldown_sec;
	float container_spawn_distance_m;
	float container_spawn_max_slope_deg;
	float container_spawn_check_radius_m;
	int container_respawn_cooldown_sec;
	ref ShopClaimMessagesConfig messages;
	ref ShopClaimGuiConfig gui;

	void ShopClaimModConfig()
	{
		bridge_url = "http://127.0.0.1:8787";
		server_id = "cherno_1";
		api_token = "";
		claim_command = "wargm";
		enable_chat_commands = false;
		container_class = "SeaChest";
		container_empty_check_sec = 5;
		abandoned_container_hours = 24;
		vehicle_spawn_cooldown_sec = 30;
		container_spawn_distance_m = 1.2;
		container_spawn_max_slope_deg = 25.0;
		container_spawn_check_radius_m = 0.8;
		container_respawn_cooldown_sec = 30;
		messages = new ShopClaimMessagesConfig();
		gui = new ShopClaimGuiConfig();
	}

	bool IsValid()
	{
		return bridge_url != "" && server_id != "" && api_token != "";
	}
};

class ShopClaimSettings
{
	protected static ref ShopClaimModConfig s_Instance;
	protected static bool s_LoadAttempted;

	static ShopClaimModConfig Get()
	{
		if (!s_Instance && !s_LoadAttempted)
			Load();

		return s_Instance;
	}

	static void Load()
	{
		s_LoadAttempted = true;
		s_Instance = new ShopClaimModConfig();

		string path = ResolveProfileFile("config.json");
		if (!FileExist(path))
		{
			ShopClaimLogger.Error("Config not found: " + path);
			return;
		}

		JsonFileLoader<ShopClaimModConfig>.JsonLoadFile(path, s_Instance);
		NormalizeServerIds(s_Instance);

		if (!s_Instance.IsValid())
		{
			ShopClaimLogger.Error("Config invalid or failed to parse: " + path);
			s_Instance = null;
			return;
		}

		if (!s_Instance.claim_command || s_Instance.claim_command == "")
			s_Instance.claim_command = "wargm";

		if (!s_Instance.container_class || s_Instance.container_class == "")
			s_Instance.container_class = "SeaChest";

		if (s_Instance.container_empty_check_sec < 1)
			s_Instance.container_empty_check_sec = 5;

		if (s_Instance.container_spawn_distance_m <= 0)
			s_Instance.container_spawn_distance_m = 1.2;

		if (s_Instance.container_spawn_max_slope_deg <= 0)
			s_Instance.container_spawn_max_slope_deg = 25.0;

		if (s_Instance.container_spawn_check_radius_m <= 0)
			s_Instance.container_spawn_check_radius_m = 0.8;

		if (s_Instance.container_respawn_cooldown_sec < 1)
			s_Instance.container_respawn_cooldown_sec = 30;

		if (!s_Instance.messages)
			s_Instance.messages = new ShopClaimMessagesConfig();

		if (!s_Instance.gui)
			s_Instance.gui = new ShopClaimGuiConfig();

		s_Instance.gui.theme_prefix = SanitizeThemePrefix(s_Instance.gui.theme_prefix);

		ShopClaimLogger.Info("Config loaded: bridge=" + s_Instance.bridge_url + " server_id=" + s_Instance.server_id + " theme=" + s_Instance.gui.theme_prefix);
	}

	protected static string SanitizeThemePrefix(string prefix)
	{
		if (!prefix || prefix == "")
			return "ShopClaimTheme";

		if (prefix.Length() > 64)
			return "ShopClaimTheme";

		if (prefix.IndexOf("/") != -1)
			return "ShopClaimTheme";

		if (prefix.IndexOf("\\") != -1)
			return "ShopClaimTheme";

		if (prefix.IndexOf("..") != -1)
			return "ShopClaimTheme";

		if (prefix.IndexOf(" ") != -1)
			return "ShopClaimTheme";

		return prefix;
	}

	static string GetThemePrefix()
	{
		ShopClaimModConfig cfg = Get();
		if (!cfg || !cfg.gui)
			return "ShopClaimTheme";

		if (!cfg.gui.theme_prefix || cfg.gui.theme_prefix == "")
			return "ShopClaimTheme";

		return cfg.gui.theme_prefix;
	}

	protected static string ResolveProfileFile(string fileName)
	{
		string primary = "$profile:ShopClaim/" + fileName;
		if (FileExist(primary))
			return primary;
		string legacy = "$profile:WargmDelivery/" + fileName;
		if (FileExist(legacy))
			return legacy;
		return primary;
	}

	static string GetProfilePath(string fileName)
	{
		return ResolveProfileFile(fileName);
	}

	protected static void NormalizeServerIds(ShopClaimModConfig cfg)
	{
		if (!cfg)
			return;
		if (cfg.shop_server_id == 0 && cfg.wargm_server_id > 0)
			cfg.shop_server_id = cfg.wargm_server_id;
	}

};
