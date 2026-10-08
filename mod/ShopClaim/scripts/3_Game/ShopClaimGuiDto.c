class ShopClaimGuiSerializer
{
	static string EscapeJson(string value)
	{
		if (!value)
			return "";

		string result = "";
		string backslash = "\\";
		string quote = "\"";

		for (int i = 0; i < value.Length(); i++)
		{
			string ch = value.Substring(i, 1);
			if (ch == backslash)
				result = result + backslash + backslash;
			else if (ch == quote)
				result = result + backslash + quote;
			else if (ch == "\n")
				result = result + backslash + "n";
			else if (ch == "\r")
				result = result + backslash + "r";
			else if (ch == "\t")
				result = result + backslash + "t";
			else
				result = result + ch;
		}

		return result;
	}

	static string SerializePendingOrders(array<ref ShopClaimPendingOrder> orders)
	{
		if (!orders || orders.Count() == 0)
			return "[]";

		string json = "[";
		bool first = true;

		foreach (ShopClaimPendingOrder order : orders)
		{
			if (!order)
				continue;

			if (!first)
				json = json + ",";
			first = false;

			json = json + "{";
			json = json + "\"operation_id\":\"" + EscapeJson(order.operation_id) + "\",";
			json = json + "\"name\":\"" + EscapeJson(order.name) + "\",";
			json = json + "\"type\":\"" + EscapeJson(order.type) + "\",";
			json = json + "\"status\":\"" + EscapeJson(order.status) + "\"";
			json = json + "}";
		}

		json = json + "]";
		return json;
	}

	static string SerializePendingEnvelope(array<ref ShopClaimPendingOrder> orders, string activeContainerOperationId, string themePrefix)
	{
		string ordersJson = SerializePendingOrders(orders);
		string activeId = activeContainerOperationId;
		if (!activeId)
			activeId = "";

		string theme = themePrefix;
		if (!theme)
			theme = "ShopClaimTheme";

		return "{\"orders\":" + ordersJson + ",\"active_container_operation_id\":\"" + EscapeJson(activeId) + "\",\"theme_prefix\":\"" + EscapeJson(theme) + "\"}";
	}

	static string SerializeErrorEnvelope(string message, string themePrefix)
	{
		if (!message)
			message = "";

		string theme = themePrefix;
		if (!theme)
			theme = "ShopClaimTheme";

		return "{\"message\":\"" + EscapeJson(message) + "\",\"theme_prefix\":\"" + EscapeJson(theme) + "\"}";
	}
};
