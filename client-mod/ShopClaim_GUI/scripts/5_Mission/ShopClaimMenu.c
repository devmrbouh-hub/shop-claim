class ShopClaimMenu extends UIScriptedMenu
{
	protected static ref ShopClaimMenu s_Instance;

	protected static const string DEFAULT_THEME_PREFIX = "ShopClaimTheme";

	protected Widget m_Root;
	protected Widget m_GridOrders;
	protected TextWidget m_TextStatus;
	protected Widget m_ButtonRefresh;
	protected Widget m_ButtonRespawn;
	protected Widget m_ButtonClose;
	protected Widget m_ButtonRefreshFallback;
	protected Widget m_ButtonRespawnFallback;
	protected Widget m_ButtonCloseFallback;
	protected Widget m_OverlayDim;
	protected ref array<ref ShopClaimGuiOrderRow> m_Rows;
	protected ref array<string> m_RowOperationIds;
	protected string m_ClaimingOperationId;
	protected string m_ActiveContainerOperationId;
	protected string m_ThemePrefix;
	protected bool m_IsClaiming;
	protected bool m_IsLoading;
	protected bool m_IsRespawning;
	protected bool m_ThemePanelOk;
	protected bool m_ThemePartialBroken;
	protected bool m_RefreshThemed;
	protected bool m_CloseThemed;
	protected bool m_RespawnThemed;

	protected static const int STATUS_INFO = 0;
	protected static const int STATUS_ERROR = 1;
	protected static const int STATUS_LOADING = 2;
	protected static const int STATUS_SUCCESS = 3;

	static ShopClaimMenu GetInstance()
	{
		return s_Instance;
	}

	static bool IsOpen()
	{
		return s_Instance != null;
	}

	static void CloseIfOpen()
	{
		if (s_Instance)
			s_Instance.Close();
	}

	static void TryOpen()
	{
		if (IsOpen())
			return;

		PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
		if (!player)
			return;

		if (!CanOpenMenu(player))
			return;

		GetGame().GetUIManager().EnterScriptedMenu(MENU_SHOP_CLAIM, null);
	}

	static bool CanOpenMenu(PlayerBase player)
	{
		if (!player || !GetGame() || !GetGame().GetUIManager())
			return false;

		if (player.IsUnconscious())
			return false;

		HumanCommandVehicle vehCmd = player.GetCommand_Vehicle();
		if (vehCmd)
			return false;

		if (GetGame().GetUIManager().GetMenu() && GetGame().GetUIManager().GetMenu() != s_Instance)
			return false;

		return true;
	}

	override Widget Init()
	{
		s_Instance = this;
		m_Rows = new array<ref ShopClaimGuiOrderRow>();
		m_RowOperationIds = new array<string>();
		m_ClaimingOperationId = "";
		m_ActiveContainerOperationId = "";
		m_ThemePrefix = "";
		m_IsClaiming = false;
		m_IsLoading = true;
		m_IsRespawning = false;
		m_ThemePanelOk = false;
		m_ThemePartialBroken = false;
		m_RefreshThemed = false;
		m_CloseThemed = false;
		m_RespawnThemed = false;

		layoutRoot = GetGame().GetWorkspace().CreateWidgets("ShopClaim_GUI/gui/layouts/shop_claim_menu.layout");
		m_Root = layoutRoot;

		m_GridOrders = m_Root.FindAnyWidget("grid_orders");
		m_TextStatus = TextWidget.Cast(m_Root.FindAnyWidget("text_status"));
		m_ButtonRefresh = m_Root.FindAnyWidget("button_refresh");
		m_ButtonRespawn = m_Root.FindAnyWidget("button_respawn");
		m_ButtonClose = m_Root.FindAnyWidget("button_close");
		m_ButtonRefreshFallback = m_Root.FindAnyWidget("button_refresh_fallback");
		m_ButtonRespawnFallback = m_Root.FindAnyWidget("button_respawn_fallback");
		m_ButtonCloseFallback = m_Root.FindAnyWidget("button_close_fallback");
		m_OverlayDim = m_Root.FindAnyWidget("overlay_dim");

		m_ThemePrefix = DEFAULT_THEME_PREFIX;
		m_ThemePanelOk = ApplyThemeTextures();

		SetStatus("Загрузка…", STATUS_LOADING);
		SetButtonsEnabled(false);
		ShopClaimClientRpc.Get().RequestPendingList();

		return layoutRoot;
	}

	override void OnShow()
	{
		super.OnShow();

		if (layoutRoot)
			SetFocus(layoutRoot);

		MissionGameplay mission = MissionGameplay.Cast(GetGame().GetMission());
		if (mission)
			mission.AddActiveInputExcludes({"menu"});
	}

	override void OnHide()
	{
		MissionGameplay mission = MissionGameplay.Cast(GetGame().GetMission());
		if (mission)
			mission.RemoveActiveInputExcludes({"menu"}, false);

		super.OnHide();
		s_Instance = null;
	}

	override bool OnKeyDown(Widget w, int x, int y, int key)
	{
		if (key == KeyCode.KC_ESCAPE)
		{
			CloseMenu();
			return true;
		}

		return super.OnKeyDown(w, x, y, key);
	}

	override bool OnClick(Widget w, int x, int y, int button)
	{
		if (w == m_OverlayDim)
		{
			CloseMenu();
			return true;
		}

		if (IsClickOnEither(m_ButtonClose, m_ButtonCloseFallback, w))
		{
			CloseMenu();
			return true;
		}

		if (IsClickOnEither(m_ButtonRefresh, m_ButtonRefreshFallback, w))
		{
			BeginLoading();
			ShopClaimClientRpc.Get().RequestPendingList();
			return true;
		}

		if (IsClickOnEither(m_ButtonRespawn, m_ButtonRespawnFallback, w))
		{
			if (m_IsClaiming || m_IsLoading || m_IsRespawning)
				return true;

			m_IsRespawning = true;
			SetStatus("Пересоздание ящика…", STATUS_LOADING);
			SetButtonsEnabled(false);
			ShopClaimClientRpc.Get().RespawnContainer();
			return true;
		}

		Widget claimWidget = ResolveClaimWidget(w);
		if (claimWidget && TryClaimRow(claimWidget))
			return true;

		return super.OnClick(w, x, y, button);
	}

	override bool OnMouseButtonUp(Widget w, int x, int y, int button)
	{
		if (button != MouseState.LEFT)
			return super.OnMouseButtonUp(w, x, y, button);

		if (IsClickOnEither(m_ButtonClose, m_ButtonCloseFallback, w))
		{
			CloseMenu();
			return true;
		}

		if (IsClickOnEither(m_ButtonRefresh, m_ButtonRefreshFallback, w))
		{
			BeginLoading();
			ShopClaimClientRpc.Get().RequestPendingList();
			return true;
		}

		if (IsClickOnEither(m_ButtonRespawn, m_ButtonRespawnFallback, w))
		{
			if (m_IsClaiming || m_IsLoading || m_IsRespawning)
				return true;

			m_IsRespawning = true;
			SetStatus("Пересоздание ящика…", STATUS_LOADING);
			SetButtonsEnabled(false);
			ShopClaimClientRpc.Get().RespawnContainer();
			return true;
		}

		Widget claimWidget = ResolveClaimWidget(w);
		if (claimWidget && TryClaimRow(claimWidget))
			return true;

		return super.OnMouseButtonUp(w, x, y, button);
	}

	protected bool TryClaimRow(Widget claimWidget)
	{
		if (!claimWidget)
			return false;

		if (m_IsClaiming || m_IsLoading)
			return true;

		int rowIndex = claimWidget.GetUserID();
		if (rowIndex < 0 || rowIndex >= m_RowOperationIds.Count())
			return true;

		string operationId = m_RowOperationIds.Get(rowIndex);
		if (!operationId || operationId == "")
			return true;

		m_IsClaiming = true;
		m_ClaimingOperationId = operationId;
		SetStatus("Выдача покупки…", STATUS_LOADING);
		SetButtonsEnabled(false);
		ShopClaimClientRpc.Get().Claim(operationId);
		return true;
	}

	void OnSyncPendingList(array<ref ShopClaimGuiOrderRow> rows, string activeContainerOperationId, string themePrefix)
	{
		m_ThemePrefix = ResolveThemePrefix(themePrefix);
		m_ThemePanelOk = ApplyThemeTextures();

		m_IsLoading = false;
		m_IsClaiming = false;
		m_IsRespawning = false;
		m_ClaimingOperationId = "";
		m_ActiveContainerOperationId = activeContainerOperationId;
		m_Rows = rows;

		ClearOrderRows();
		UpdateRespawnButton();

		if (!rows || rows.Count() == 0)
		{
			SetStatusWithThemeWarning("Нет незабранных покупок.", STATUS_INFO);
			SetButtonsEnabled(true);
			return;
		}

		SetStatusWithThemeWarning("", STATUS_INFO);
		PopulateOrderRows(rows);
		SetButtonsEnabled(true);
	}

	void OnSyncPendingError(string message, string themePrefix)
	{
		m_ThemePrefix = ResolveThemePrefix(themePrefix);
		m_ThemePanelOk = ApplyThemeTextures();

		m_IsLoading = false;
		m_IsClaiming = false;
		m_IsRespawning = false;
		m_ClaimingOperationId = "";
		ClearOrderRows();
		UpdateRespawnButton();

		if (!message || message == "")
			message = "Не удалось загрузить список.";

		SetStatusWithThemeWarning(message, STATUS_ERROR);
		SetButtonsEnabled(true);
	}

	void OnClaimResult(bool ok, string message, bool closeMenu)
	{
		m_IsClaiming = false;
		m_IsRespawning = false;
		m_ClaimingOperationId = "";

		if (!message || message == "")
		{
			if (ok)
				message = "Покупка выдана.";
			else
				message = "Не удалось выдать покупку.";
		}

		if (ok)
			SetStatus(message, STATUS_SUCCESS);
		else
		{
			SetStatus(message, STATUS_ERROR);
			if (!ok && m_ActiveContainerOperationId && m_ActiveContainerOperationId != "")
				UpdateRespawnButton(true);
		}
		SetButtonsEnabled(true);

		if (ok)
			ShopClaimClientRpc.Get().RequestPendingList();

		if (closeMenu)
		{
			GetGame().GetCallQueue(CALL_CATEGORY_GUI).CallLater(CloseMenu, 1500, false);
		}
	}

	protected void BeginLoading()
	{
		m_IsLoading = true;
		m_IsClaiming = false;
		m_IsRespawning = false;
		m_ClaimingOperationId = "";
		ClearOrderRows();
		SetStatus("Загрузка…", STATUS_LOADING);
		SetButtonsEnabled(false);
	}

	protected string ResolveThemePrefix(string fromRpc)
	{
		if (fromRpc && fromRpc != "")
			return fromRpc;

		return DEFAULT_THEME_PREFIX;
	}

	protected void UpdateRespawnButton(bool highlight = false)
	{
		bool show = m_ActiveContainerOperationId && m_ActiveContainerOperationId != "";

		if (m_RespawnThemed)
		{
			if (m_ButtonRespawn)
				m_ButtonRespawn.Show(show);
			if (m_ButtonRespawnFallback)
				m_ButtonRespawnFallback.Show(false);
		}
		else
		{
			if (m_ButtonRespawnFallback)
				m_ButtonRespawnFallback.Show(show);
			if (m_ButtonRespawn)
				m_ButtonRespawn.Show(false);
		}
	}

	protected void PopulateOrderRows(array<ref ShopClaimGuiOrderRow> rows)
	{
		if (!m_GridOrders)
			return;

		m_RowOperationIds.Clear();

		int rowIndex = 0;
		foreach (ShopClaimGuiOrderRow row : rows)
		{
			if (!row)
				continue;

			Widget rowWidget = GetGame().GetWorkspace().CreateWidgets("ShopClaim_GUI/gui/layouts/shop_claim_row.layout", m_GridOrders);
			if (!rowWidget)
				continue;

			m_RowOperationIds.Insert(row.operation_id);

			TextWidget typeText = TextWidget.Cast(rowWidget.FindAnyWidget("text_type"));
			TextWidget nameText = TextWidget.Cast(rowWidget.FindAnyWidget("text_name"));
			TextWidget badgeText = TextWidget.Cast(rowWidget.FindAnyWidget("text_badge"));
			Widget claimBtn = rowWidget.FindAnyWidget("button_claim");
			Widget claimFallback = rowWidget.FindAnyWidget("button_claim_fallback");

			if (claimBtn)
				claimBtn.SetUserID(rowIndex);
			if (claimFallback)
				claimFallback.SetUserID(rowIndex);

			ApplyThemeButtonPair(rowWidget, "button_claim", "button_claim_img", "button_claim_fallback", BuildThemeTexturePath("Claim_button.edds"));

			rowIndex++;

			if (typeText)
			{
				if (row.type == "vehicle")
					typeText.SetText("[Техника]");
				else
					typeText.SetText("[Предметы]");
			}

			if (nameText)
				nameText.SetText(row.name);

			if (badgeText)
			{
				if (row.status == "spawned")
					badgeText.SetText("Выдано");
				else
					badgeText.SetText("");
			}
		}

		GridSpacerWidget grid = GridSpacerWidget.Cast(m_GridOrders);
		if (grid)
			grid.Update();
	}

	protected void ClearOrderRows()
	{
		if (!m_GridOrders)
			return;

		Widget child = m_GridOrders.GetChildren();
		while (child)
		{
			Widget next = child.GetSibling();
			child.Unlink();
			child = next;
		}

		m_RowOperationIds.Clear();
	}

	protected void SetStatus(string text, int statusKind = STATUS_INFO)
	{
		if (!m_TextStatus)
			return;

		m_TextStatus.SetText(text);

		if (!text || text == "")
			return;

		switch (statusKind)
		{
			case STATUS_ERROR:
				m_TextStatus.SetColor(ARGB(255, 191, 89, 26));
				break;
			case STATUS_SUCCESS:
				m_TextStatus.SetColor(ARGB(255, 38, 89, 51));
				break;
			case STATUS_LOADING:
			case STATUS_INFO:
			default:
				m_TextStatus.SetColor(ARGB(255, 51, 56, 71));
				break;
		}
	}

	protected void SetStatusWithThemeWarning(string text, int statusKind = STATUS_INFO)
	{
		if (!m_ThemePanelOk)
		{
			if (m_ThemePartialBroken)
			{
				string themeWarning = "Не удалось загрузить подложку темы: " + m_ThemePrefix;
				if (!text || text == "")
					text = themeWarning;
				else
					text = text + " " + themeWarning;

				statusKind = STATUS_ERROR;
			}
			else
			{
				SetStatus(text, statusKind);
				return;
			}
		}

		SetStatus(text, statusKind);
	}

	protected void SetButtonsEnabled(bool enabled)
	{
		SetFooterButtonEnabled(m_ButtonRefresh, m_ButtonRefreshFallback, m_RefreshThemed, enabled);

		bool respawnEnabled = enabled && !m_IsClaiming && !m_IsRespawning;
		bool respawnVisible = false;
		if (m_RespawnThemed && m_ButtonRespawn)
			respawnVisible = m_ButtonRespawn.IsVisible();
		else if (!m_RespawnThemed && m_ButtonRespawnFallback)
			respawnVisible = m_ButtonRespawnFallback.IsVisible();
		SetFooterButtonEnabled(m_ButtonRespawn, m_ButtonRespawnFallback, m_RespawnThemed, respawnEnabled && respawnVisible);

		SetFooterButtonEnabled(m_ButtonClose, m_ButtonCloseFallback, m_CloseThemed, true);

		if (!m_GridOrders)
			return;

		Widget child = m_GridOrders.GetChildren();
		while (child)
		{
			Widget claimBtn = child.FindAnyWidget("button_claim");
			Widget claimFallback = child.FindAnyWidget("button_claim_fallback");
			bool claimThemed = claimBtn && claimBtn.IsVisible();

			if (claimThemed)
				SetWidgetInteractive(claimBtn, enabled && !m_IsClaiming);
			else
			{
				ButtonWidget claimButton = ButtonWidget.Cast(claimFallback);
				if (claimButton)
					claimButton.Enable(enabled && !m_IsClaiming);
			}

			child = child.GetSibling();
		}
	}

	protected void SetFooterButtonEnabled(Widget themed, Widget fallback, bool useThemed, bool interactive)
	{
		ButtonWidget fallbackBtn = ButtonWidget.Cast(fallback);

		if (useThemed)
		{
			SetWidgetInteractive(themed, interactive);
			if (fallbackBtn)
				fallbackBtn.Enable(false);
		}
		else
		{
			SetWidgetInteractive(themed, false);
			if (fallbackBtn)
				fallbackBtn.Enable(interactive);
		}
	}

	protected void SetWidgetInteractive(Widget w, bool interactive)
	{
		if (!w)
			return;

		if (interactive)
			w.ClearFlags(WidgetFlags.IGNOREPOINTER);
		else
			w.SetFlags(WidgetFlags.IGNOREPOINTER);
	}

	protected void CloseMenu()
	{
		Close();
	}

	protected string BuildThemeTexturePath(string fileName)
	{
		if (!m_ThemePrefix || m_ThemePrefix == "")
			m_ThemePrefix = DEFAULT_THEME_PREFIX;

		return m_ThemePrefix + "/gui/textures/" + fileName;
	}

	protected bool ApplyPanelBackdrop()
	{
		if (!m_Root)
			return false;

		bool panelThemed = LoadWidgetImage(m_Root, "panel_root_img", BuildThemeTexturePath("store_menu.edds"));

		Widget panelImg = m_Root.FindAnyWidget("panel_root_img");
		if (panelImg)
			panelImg.Show(panelThemed);

		m_ThemePanelOk = panelThemed;
		return panelThemed;
	}

	protected bool ApplyThemeTextures()
	{
		if (!m_Root)
			return false;

		m_ThemePartialBroken = false;

		bool panelThemed = ApplyPanelBackdrop();

		bool titleThemed = ApplyThemeTexturePair(m_Root, "text_title", "text_title_fallback", BuildThemeTexturePath("logo.edds"));
		bool subtitleThemed = ApplyThemeTexturePair(m_Root, "text_subtitle", "text_subtitle_fallback", BuildThemeTexturePath("TEXT_pokupki.edds"));
		m_RefreshThemed = ApplyThemeButtonPair(m_Root, "button_refresh", "button_refresh_img", "button_refresh_fallback", BuildThemeTexturePath("refresh_button.edds"));
		m_CloseThemed = ApplyThemeButtonPair(m_Root, "button_close", "button_close_img", "button_close_fallback", BuildThemeTexturePath("Close_button.edds"));
		m_RespawnThemed = ApplyThemeButtonPair(m_Root, "button_respawn", "button_respawn_img", "button_respawn_fallback", BuildThemeTexturePath("respawn_button.edds"));
		ApplyThemeTexturePair(m_Root, "text_hint", "text_hint_fallback", BuildThemeTexturePath("TEXT_MEMO.edds"));

		if (!panelThemed && (titleThemed || subtitleThemed || m_RefreshThemed || m_CloseThemed || m_RespawnThemed))
			m_ThemePartialBroken = true;

		return panelThemed;
	}

	protected bool ApplyThemeTexturePair(Widget scope, string imageName, string fallbackName, string eddsPath)
	{
		bool ok = LoadWidgetImage(scope, imageName, eddsPath);

		Widget imageWidget = scope.FindAnyWidget(imageName);
		Widget fallbackWidget = scope.FindAnyWidget(fallbackName);

		if (imageWidget)
			imageWidget.Show(ok);
		if (fallbackWidget)
			fallbackWidget.Show(!ok);

		return ok;
	}

	protected bool ApplyThemeButtonPair(Widget scope, string panelName, string imageName, string fallbackName, string eddsPath)
	{
		bool ok = LoadWidgetImage(scope, imageName, eddsPath);

		Widget panelWidget = scope.FindAnyWidget(panelName);
		Widget fallbackWidget = scope.FindAnyWidget(fallbackName);

		if (panelWidget)
			panelWidget.Show(ok);
		if (fallbackWidget)
			fallbackWidget.Show(!ok);

		return ok;
	}

	protected bool LoadWidgetImage(Widget scope, string widgetName, string eddsPath)
	{
		if (!scope || !widgetName || widgetName == "" || !eddsPath || eddsPath == "")
			return false;

		ImageWidget image = ImageWidget.Cast(scope.FindAnyWidget(widgetName));
		if (!image)
			return false;

		if (!image.LoadImageFile(0, eddsPath))
			return false;

		image.SetImage(0);
		image.SetFlags(image.GetFlags() | WidgetFlags.STRETCH);
		return true;
	}

	protected bool IsClickOnEither(Widget themed, Widget fallback, Widget clicked)
	{
		if (IsClickOn(themed, clicked))
			return true;

		if (IsClickOn(fallback, clicked))
			return true;

		return false;
	}

	protected bool IsClickOn(Widget target, Widget clicked)
	{
		if (!target || !clicked)
			return false;

		if (clicked == target)
			return true;

		Widget parent = clicked.GetParent();
		while (parent)
		{
			if (parent == target)
				return true;

			parent = parent.GetParent();
		}

		return false;
	}

	protected Widget ResolveClaimWidget(Widget clicked)
	{
		if (!clicked)
			return null;

		string name = clicked.GetName();
		if (name == "button_claim" || name == "button_claim_fallback")
			return clicked;

		Widget parent = clicked.GetParent();
		while (parent)
		{
			name = parent.GetName();
			if (name == "button_claim" || name == "button_claim_fallback")
				return parent;

			parent = parent.GetParent();
		}

		return null;
	}
};

const int MENU_SHOP_CLAIM = 987654321;

modded class MissionBase
{
	override UIScriptedMenu CreateScriptedMenu(int id)
	{
		if (id == MENU_SHOP_CLAIM)
			return new ShopClaimMenu();

		return super.CreateScriptedMenu(id);
	}
};

