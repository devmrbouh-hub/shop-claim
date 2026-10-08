class ShopClaimOrderPresenter
{
	static void SendOrderList(PlayerBase player, array<ref ShopClaimPendingOrder> orders)
	{
		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (!cfg || !cfg.messages)
			return;

		if (!orders || orders.Count() == 0)
		{
			ShopClaimPlayerMessenger.Send(player, cfg.messages.no_purchases);
			return;
		}

		string command = cfg.claim_command;
		if (command == "")
			command = "wargm";

		string body = "Ваши покупки:";
		for (int i = 0; i < orders.Count(); i++)
		{
			ShopClaimPendingOrder order = orders.Get(i);
			if (!order)
				continue;

			string typeLabel = "[Предметы]";
			if (order.IsVehicle())
				typeLabel = "[Техника]";

			string statusSuffix = "";
			if (order.IsSpawned())
				statusSuffix = " [Выдано, заберите лут]";

			body = body + "\n  " + (i + 1).ToString() + ". " + typeLabel + " " + order.name + statusSuffix;
		}

		body = body + "\n/" + command + " <номер> — забрать";
		ShopClaimPlayerMessenger.Send(player, body);
	}
};
