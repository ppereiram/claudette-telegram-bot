#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.IO;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
#endregion

/*
DailyPnLReporter.cs
====================
Corre en cualquier chart de MNQ (1-min o 5-min).
A las 4:00 PM ET escribe automaticamente un JSON con el P&L del dia
por cada cuenta Sim en:
  C:\Users\Pablo\Documents\Obsidian Vault\Trader Bot\
  Bot_Quant_IA\market_logs\strategies_pnl_YYYY-MM-DD.json

market_monitor_logger.py detecta ese archivo y lo fusiona
automaticamente en el log del dia.
*/

namespace NinjaTrader.NinjaScript.Strategies
{
    public class DailyPnLReporter : Strategy
    {
        private bool reportWritten = false;
        private DateTime lastReportDate = DateTime.MinValue;

        // Cuentas a ignorar (no son estrategias Sim)
        private readonly HashSet<string> ignoredAccounts = new HashSet<string>
        {
            "Sim101", "ACCOUNT 2", "1146189"
        };

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name            = "DailyPnLReporter";
                Description     = "Exporta P&L diario por cuenta Sim al cierre del mercado";
                Calculate       = Calculate.OnBarClose;
                IsOverlay       = true;
                IsAutoScale     = false;

                ExportHour      = 16;   // 4:00 PM ET
                ExportMinute    = 1;
                VaultPath       = @"C:\Users\Pablo\Documents\Obsidian Vault\Trader Bot\Bot_Quant_IA\market_logs";
            }
        }

        protected override void OnBarUpdate()
        {
            // Reset flag al inicio de cada dia
            if (Time[0].Date != lastReportDate.Date)
                reportWritten = false;

            // Disparar reporte a la hora configurada
            int triggerTime = ExportHour * 10000 + ExportMinute * 100;
            if (!reportWritten && ToTime(Time[0]) >= triggerTime)
            {
                WriteReport();
                reportWritten    = true;
                lastReportDate   = Time[0];
            }
        }

        private void WriteReport()
        {
            try
            {
                string today    = Time[0].ToString("yyyy-MM-dd");
                string filename = $"strategies_pnl_{today}.json";
                string filepath = Path.Combine(VaultPath, filename);

                var lines = new List<string>();

                foreach (Account account in Account.All)
                {
                    if (ignoredAccounts.Contains(account.Name))
                        continue;
                    if (!account.Name.StartsWith("Sim"))
                        continue;

                    double pnl = account.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
                    lines.Add($"    \"{account.Name}\": {Math.Round(pnl, 2)}");
                }

                if (lines.Count == 0)
                {
                    Print("[DailyPnLReporter] No se encontraron cuentas Sim activas.");
                    return;
                }

                var sb = new StringBuilder();
                sb.AppendLine("{");
                sb.AppendLine($"  \"fecha\": \"{today}\",");
                sb.AppendLine($"  \"timestamp\": \"{DateTime.Now:yyyy-MM-ddTHH:mm:ss}\",");
                sb.AppendLine("  \"strategies_pnl\": {");
                sb.AppendLine(string.Join(",\n", lines));
                sb.AppendLine("  }");
                sb.Append("}");

                Directory.CreateDirectory(VaultPath);
                File.WriteAllText(filepath, sb.ToString(), Encoding.UTF8);

                Print($"[DailyPnLReporter] Reporte guardado: {filepath}");
                Print($"[DailyPnLReporter] {lines.Count} cuentas exportadas.");
            }
            catch (Exception ex)
            {
                Print($"[DailyPnLReporter] ERROR: {ex.Message}");
            }
        }

        #region Properties
        [Display(Name = "Hora exportacion (ET)", GroupName = "Configuracion", Order = 1)]
        public int ExportHour { get; set; }

        [Display(Name = "Minuto exportacion", GroupName = "Configuracion", Order = 2)]
        public int ExportMinute { get; set; }

        [Display(Name = "Ruta vault", GroupName = "Configuracion", Order = 3)]
        public string VaultPath { get; set; }
        #endregion
    }
}
