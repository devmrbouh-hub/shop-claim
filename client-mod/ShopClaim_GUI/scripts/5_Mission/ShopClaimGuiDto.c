class ShopClaimGuiOrderRow
{
	string operation_id;
	string name;
	string type;
	string status;

	void ShopClaimGuiOrderRow()
	{
		operation_id = "";
		name = "";
		type = "";
		status = "";
	}
};

class ShopClaimGuiDto
{
	static int IndexOfFrom(string haystack, int from, string needle)
	{
		if (from >= haystack.Length())
			return -1;

		string tail = haystack.Substring(from, haystack.Length() - from);
		int idx = tail.IndexOf(needle);
		if (idx < 0)
			return -1;

		return from + idx;
	}

	static string ReadJsonString(string json, string key)
	{
		string pattern = "\"" + key + "\":\"";
		int start = json.IndexOf(pattern);
		if (start < 0)
			return "";

		start = start + pattern.Length();
		string result = "";

		for (int i = start; i < json.Length(); i++)
		{
			string ch = json.Substring(i, 1);
			if (ch == "\\")
			{
				if (i + 1 < json.Length())
				{
					string next = json.Substring(i + 1, 1);
					if (next == "n")
						result = result + "\n";
					else if (next == "r")
						result = result + "\r";
					else if (next == "t")
						result = result + "\t";
					else
						result = result + next;
					i++;
				}
				continue;
			}

			if (ch == "\"")
				break;

			result = result + ch;
		}

		return result;
	}

	static string ExtractOrdersArrayJson(string json)
	{
		if (!json || json == "")
			return json;

		string trimmed = json;
		trimmed.Trim();

		if (trimmed.Length() > 0 && trimmed.Substring(0, 1) == "[")
			return trimmed;

		int ordersKey = json.IndexOf("\"orders\"");
		if (ordersKey < 0)
			return json;

		int arrayStart = IndexOfFrom(json, ordersKey, "[");
		if (arrayStart < 0)
			return "[]";

		int depth = 0;
		for (int i = arrayStart; i < json.Length(); i++)
		{
			string ch = json.Substring(i, 1);
			if (ch == "[")
				depth++;
			else if (ch == "]")
			{
				depth--;
				if (depth == 0)
					return json.Substring(arrayStart, i - arrayStart + 1);
			}
		}

		return "[]";
	}

	static bool ParsePendingEnvelope(string json, out array<ref ShopClaimGuiOrderRow> rows, out string activeContainerOperationId, out string themePrefix)
	{
		activeContainerOperationId = "";
		themePrefix = "";

		if (!json || json == "" || json == "[]")
		{
			rows = new array<ref ShopClaimGuiOrderRow>();
			return true;
		}

		string trimmed = json;
		trimmed.Trim();

		if (trimmed.Length() > 0 && trimmed.Substring(0, 1) == "{")
		{
			activeContainerOperationId = ReadJsonString(json, "active_container_operation_id");
			themePrefix = ReadJsonString(json, "theme_prefix");
		}

		string ordersJson = ExtractOrdersArrayJson(json);
		return ParsePendingOrders(ordersJson, rows);
	}

	static void ParseSyncPendingError(string payload, out string message, out string themePrefix)
	{
		message = "";
		themePrefix = "";

		if (!payload || payload == "")
			return;

		string trimmed = payload;
		trimmed.Trim();

		if (trimmed.Length() > 0 && trimmed.Substring(0, 1) == "{")
		{
			message = ReadJsonString(payload, "message");
			themePrefix = ReadJsonString(payload, "theme_prefix");
			return;
		}

		message = payload;
	}

	static bool ParsePendingOrders(string json, out array<ref ShopClaimGuiOrderRow> rows)
	{
		rows = new array<ref ShopClaimGuiOrderRow>();
		if (!json || json == "" || json == "[]")
			return true;

		int pos = 0;
		while (true)
		{
			int objStart = IndexOfFrom(json, pos, "{");
			if (objStart < 0)
				break;

			int objEnd = IndexOfFrom(json, objStart, "}");
			if (objEnd < 0)
				break;

			string chunk = json.Substring(objStart, objEnd - objStart + 1);
			ref ShopClaimGuiOrderRow row = new ShopClaimGuiOrderRow();
			row.operation_id = ReadJsonString(chunk, "operation_id");
			row.name = ReadJsonString(chunk, "name");
			row.type = ReadJsonString(chunk, "type");
			row.status = ReadJsonString(chunk, "status");
			rows.Insert(row);

			pos = objEnd + 1;
		}

		return true;
	}
};
