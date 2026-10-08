#!/usr/bin/env python3
"""Restore mod .c from wargm-delivery and apply ShopClaim renames (UTF-8 safe)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "services" / "wargm-delivery" / "mod" / "WargmDelivery" / "scripts"
DST = ROOT / "services" / "shop-claim" / "mod" / "ShopClaim" / "scripts"

REPLACEMENTS = [
    ("WargmDelivery_GUI", "ShopClaim_GUI"),
    ("WargmBridgeCallback", "ShopClaimHttpCallback"),
    ("WargmBridgeRequestType", "ShopClaimHttpRequestType"),
    ("WargmBridgeRequest", "ShopClaimHttpRequest"),
    ("WargmBridgeClient", "ShopClaimHttpClient"),
    ("WARGM_RPC_", "SC_RPC_"),
    ("WargmDelivery", "ShopClaim"),
    ("WargmTheme", "ShopClaimTheme"),
    ("$profile:WargmDelivery", "$profile:ShopClaim"),
    ("wargm_server_id", "shop_server_id"),
    ("Wargm", "ShopClaim"),
]

for src in SRC.rglob("Wargm*.c"):
    rel = src.relative_to(SRC)
    name = rel.name.replace("Wargm", "ShopClaim", 1)
    dst = DST / rel.parent / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8-sig")
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    text = text.replace("class ShopClaimConfig", "class ShopClaimSettings")
    text = text.replace("ShopClaimConfig.Get(", "ShopClaimSettings.Get(")
    text = text.replace("ShopClaimConfig.Load(", "ShopClaimSettings.Load(")
    text = text.replace("ShopClaimConfig.GetThemePrefix(", "ShopClaimSettings.GetThemePrefix(")
    dst.write_text(text, encoding="utf-8")
    print(dst.relative_to(ROOT))

# Re-apply ShopClaimModConfig enhancements
mod_cfg = DST / "3_Game" / "ShopClaimModConfig.c"
text = mod_cfg.read_text(encoding="utf-8")
if "wargm_server_id" not in text:
    text = text.replace(
        "int shop_server_id;\n\tstring claim_command;",
        "int shop_server_id;\n\tint wargm_server_id;\n\tstring claim_command;",
    )
if "ResolveProfileFile" not in text:
    text = text.replace(
        '\t\tstring path = "$profile:ShopClaim/config.json";\n\t\tif (!FileExist(path))',
        '\t\tstring path = ResolveProfileFile("config.json");\n\t\tif (!FileExist(path))',
    )
    text = text.replace(
        "\t\tJsonFileLoader<ShopClaimModConfig>.JsonLoadFile(path, s_Instance);\n\n\t\tif (!s_Instance.IsValid())",
        "\t\tJsonFileLoader<ShopClaimModConfig>.JsonLoadFile(path, s_Instance);\n\t\tNormalizeServerIds(s_Instance);\n\n\t\tif (!s_Instance.IsValid())",
    )
    extra = '''
\tprotected static string ResolveProfileFile(string fileName)
\t{
\t\tstring primary = "$profile:ShopClaim/" + fileName;
\t\tif (FileExist(primary))
\t\t\treturn primary;
\t\tstring legacy = "$profile:WargmDelivery/" + fileName;
\t\tif (FileExist(legacy))
\t\t\treturn legacy;
\t\treturn primary;
\t}

\tstatic string GetProfilePath(string fileName)
\t{
\t\treturn ResolveProfileFile(fileName);
\t}

\tprotected static void NormalizeServerIds(ShopClaimModConfig cfg)
\t{
\t\tif (!cfg)
\t\t\treturn;
\t\tif (cfg.shop_server_id == 0 && cfg.wargm_server_id > 0)
\t\t\tcfg.shop_server_id = cfg.wargm_server_id;
\t}
'''
    text = text.rstrip()
    if text.endswith("};"):
        text = text[:-2] + extra + "\n};\n"
mod_cfg.write_text(text, encoding="utf-8")

# Logger profile path
logger = DST / "3_Game" / "ShopClaimLogger.c"
lt = logger.read_text(encoding="utf-8")
if "GetLogFile" not in lt:
    lt = lt.replace(
        'protected static const string LOG_FILE = "$profile:ShopClaim/mod.log";',
        'protected static string GetLogFile()\n\t{\n\t\treturn ShopClaimSettings.GetProfilePath("mod.log");\n\t}',
    )
    lt = lt.replace("OpenFile(LOG_FILE,", "OpenFile(GetLogFile(),")
    logger.write_text(lt, encoding="utf-8")

# Chat handler with /wargm alias
chat_content = r'''class ShopClaimChatHandler
{
	static bool HandleCommand(PlayerBase player, string text)
	{
		if (!player)
			return false;

		if (!text || text == "")
			return false;

		text = ShopClaimJsonHelper.TrimString(text);
		if (text == "")
			return false;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (!cfg || !cfg.IsValid())
			return false;

		if (!cfg.enable_chat_commands)
			return false;

		string command = cfg.claim_command;
		if (command == "")
			command = "shop";

		if (!MatchesCommandPrefix(text, command))
			return false;

		string prefix = "/" + command;
		if (text.IndexOf("/wargm") == 0)
			prefix = "/wargm";

		string tail = text.Substring(prefix.Length(), text.Length() - prefix.Length());
		tail = ShopClaimJsonHelper.TrimString(tail);

		if (tail == "")
		{
			ShopClaimHttpClient.Get().RequestPendingList(player);
			return true;
		}

		if (tail == "respawn" || tail == "пересоздать")
		{
			ShopClaimService.Get().RespawnContainer(player, ShopClaimNotifyChannel.CHAT);
			return true;
		}

		if (tail == "cancel" || tail == "отмена")
		{
			ShopClaimPlayerMessenger.Send(player, "Команда отмены отключена. Используйте /" + command + " respawn или кнопку в меню магазина.");
			return true;
		}

		int index = tail.ToInt();
		if (index < 1)
		{
			ShopClaimPlayerMessenger.Send(player, cfg.messages.invalid_index);
			return true;
		}

		ShopClaimHttpClient.Get().RequestClaimByIndex(player, index);
		return true;
	}

	protected static bool MatchesCommandPrefix(string text, string command)
	{
		if (text.IndexOf("/" + command) == 0)
			return true;
		if (command == "shop" && text.IndexOf("/wargm") == 0)
			return true;
		return false;
	}

	static bool TryHandle(ChatMessageEventParams params)
	{
		if (!params)
			return false;

		string senderName = params.param2;
		string text = params.param3;

		PlayerBase player = FindPlayerByName(senderName);
		if (!player)
			return false;

		return HandleCommand(player, text);
	}

	protected static PlayerBase FindPlayerByName(string name)
	{
		array<Man> players = new array<Man>();
		GetGame().GetPlayers(players);

		foreach (Man man : players)
		{
			PlayerBase player = PlayerBase.Cast(man);
			if (!player || !player.GetIdentity())
				continue;

			if (player.GetIdentity().GetName() == name)
				return player;
		}

		return null;
	}
};
'''
chat = DST / "4_World" / "ShopClaimChatHandler.c"
chat.write_text(chat_content, encoding="utf-8")

print("mod scripts restored")
