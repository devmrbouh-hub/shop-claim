class ShopClaimMessagesConfig
{
	string prefix;
	string no_purchases;
	string container_active;
	string vehicle_no_space;
	string delivered_container;
	string delivered_vehicle;
	string service_unavailable;
	string please_wait;
	string vehicle_not_available;
	string invalid_index;
	string list_stale;
	string claim_failed;
	string container_bad_surface;
	string container_respawn_ok;
	string container_respawn_none;
	string container_nothing_left;

	void ShopClaimMessagesConfig()
	{
		prefix = "[Магазин]";
		no_purchases = "Нет незабранных покупок.";
		container_active = "Сначала заберите предметы из ящика или нажмите «Пересоздать ящик».";
		vehicle_no_space = "Нет места для техники. Отойдите в открытую область и попробуйте снова.";
		delivered_container = "Ящик с покупкой создан рядом с вами.";
		delivered_vehicle = "Техника выдана.";
		service_unavailable = "Сервис магазина временно недоступен.";
		please_wait = "Подождите…";
		vehicle_not_available = "Выдача техники будет в следующем обновлении.";
		invalid_index = "Неверный номер покупки.";
		list_stale = "Обновите список покупок.";
		claim_failed = "Не удалось выдать покупку.";
		container_bad_surface = "Заберите покупку на суше, не у воды.";
		container_respawn_ok = "Ящик пересоздан. Заберите оставшиеся предметы.";
		container_respawn_none = "Нет активного ящика для пересоздания.";
		container_nothing_left = "Все предметы уже получены.";
	}
};
