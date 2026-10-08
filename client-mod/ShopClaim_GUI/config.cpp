class CfgPatches
{
	class ShopClaim_GUI
	{
		units[] = {};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "JM_CF_Scripts"};
	};
};

class CfgMods
{
	class ShopClaim_GUI
	{
		dir = "ShopClaim_GUI";
		picture = "";
		action = "";
		hideName = 1;
		hidePicture = 1;
		name = "ShopClaim Delivery GUI";
		credits = "Cherno";
		author = "Cherno";
		authorID = "0";
		version = "1.0";
		extra = 0;
		type = "mod";
		dependencies[] = {"Game", "Mission"};
		inputs = "ShopClaim_GUI/inputs/inputs.xml";
		class defs
		{
		class missionScriptModule
		{
			value = "";
			files[] = {"ShopClaim_GUI/scripts/5_Mission"};
		};
		};
	};
};
