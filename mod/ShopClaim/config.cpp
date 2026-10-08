class CfgPatches
{
	class ShopClaim
	{
		units[] = {};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] = {"DZ_Data", "DZ_Gear_Containers", "JM_CF_Scripts"};
	};
};

class CfgMods
{
	class ShopClaim
	{
		dir = "ShopClaim";
		picture = "";
		action = "";
		hideName = 1;
		hidePicture = 1;
		name = "Shop Claim";
		credits = "Cherno";
		author = "Cherno";
		authorID = "0";
		version = "1.0";
		extra = 0;
		type = "mod";
		dependencies[] = {"Game", "World", "Mission"};
		class defs
		{
			class gameScriptModule
			{
				value = "";
				files[] = {"ShopClaim/scripts/3_Game"};
			};
			class worldScriptModule
			{
				value = "";
				files[] = {"ShopClaim/scripts/4_World"};
			};
			class missionScriptModule
			{
				value = "";
				files[] = {"ShopClaim/scripts/5_Mission"};
			};
		};
	};
};
