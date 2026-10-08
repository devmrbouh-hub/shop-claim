class ShopClaimLogger
{
	protected static string GetLogFile()
	{
		return ShopClaimSettings.GetProfilePath("mod.log");
	}

	static void Info(string msg)
	{
		string line = "[ShopClaim] " + msg;
		Print(line);
		AppendFile(line);
	}

	static void Error(string msg)
	{
		string line = "[ShopClaim][ERROR] " + msg;
		Print(line);
		AppendFile(line);
	}

	protected static void AppendFile(string line)
	{
		FileHandle fh = OpenFile(GetLogFile(), FileMode.APPEND);
		if (fh != 0)
		{
			FPrintln(fh, line);
			CloseFile(fh);
		}
	}
};
