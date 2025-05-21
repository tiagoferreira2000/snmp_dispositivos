using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using Serilog;
using SnmpSharpNet;
using System.Text.Json;
using System.Linq;
using System.Text;
using Serilog.Sinks.File;

class Program
{
    static string logDir = "logs";
    static string logPath = "";

    static async Task Main(string[] args)
    {
        // Carregar config.ini manualmente
        var config = LoadIniConfig("config.ini");

        int loglevel = int.TryParse(config.GetValueOrDefault("loglevel"), out var lvl) ? lvl : 0;
        int logDays = int.TryParse(config.GetValueOrDefault("log_days"), out var days) ? days : 7;

        // Configurar diretório e arquivo de log
        var hoje = DateTime.Now.ToString("yyyy-MM-dd");
        logDir = Path.Combine(Directory.GetCurrentDirectory(), "logs");
        Directory.CreateDirectory(logDir);
        logPath = Path.Combine(logDir, $"snmp_log_{hoje}.txt");
        CleanupOldLogs(logDir, logDays);

        // Configurar Serilog
        var level = loglevel == 2 ? Serilog.Events.LogEventLevel.Debug :
                    loglevel == 1 ? Serilog.Events.LogEventLevel.Information :
                    Serilog.Events.LogEventLevel.Error;
        Log.Logger = new LoggerConfiguration()
            .MinimumLevel.Is(level)
            .WriteTo.Console()
            .WriteTo.File(logPath, encoding: Encoding.UTF8, rollingInterval: Serilog.RollingInterval.Day)
            .CreateLogger();

        try
        {
            Log.Information($"FileHandler Caminho do ficheiro de logs: {logPath}");
            Log.Information("Lendo dispositivos da API...");
            var devices = await GetDevicesFromApi(config["service_url"], config["api_key"], config["api_secret"], config["client_code"]);

            var collectedData = new List<object>();
            foreach (var device in devices)
            {
                Log.Information($"Coletando SNMP de {device.nome_de_dispositivo} ({device.ip_address})");
                var paramData = new List<object>();
                if (device.parameter != null)
                {
                    foreach (var param in device.parameter)
                    {
                        var value = GetSnmpValue(device.ip_address, param.mib);
                        paramData.Add(new { parameter = param.parameter, value });
                        Log.Information($"MIB {param.mib} ({param.parameter}): {value}");
                    }
                }
                collectedData.Add(new { device = device.nome_de_dispositivo, ip = device.ip_address, parameters = paramData });
            }

            var result = await SendDataToApi(config, collectedData);
            if (result != null)
            {
                Console.WriteLine("Status code: 200");
                Console.WriteLine($"Response text: {JsonSerializer.Serialize(collectedData)}");
                Console.WriteLine("Dados enviados com sucesso.");
                Log.Information("Execução concluída com sucesso.");
            }
            else
            {
                Console.WriteLine("Falha ao enviar dados.");
                Log.Warning("Execução concluída com falha no envio.");
            }
        }
        catch (Exception ex)
        {
            Log.Error(ex, "Erro na execução do programa");
        }
        finally
        {
            Log.CloseAndFlush();
        }
        Console.WriteLine("Pressione Enter para sair...");
        Console.ReadLine();
    }

    static void CleanupOldLogs(string logDir, int logDays)
    {
        var files = Directory.GetFiles(logDir, "snmp_log_*.txt").OrderBy(f => f).ToList();
        var limite = DateTime.Now.AddDays(-logDays);
        foreach (var file in files)
        {
            var name = Path.GetFileName(file);
            var dateStr = name.Substring("snmp_log_".Length, "yyyy-MM-dd".Length);
            if (DateTime.TryParse(dateStr, out var dataLog) && dataLog < limite)
            {
                try { File.Delete(file); }
                catch (Exception e) { Console.WriteLine($"Erro ao tentar remover log antigo {name}: {e.Message}"); }
            }
        }
    }

    static Dictionary<string, string> LoadIniConfig(string path)
    {
        var dict = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var line in File.ReadAllLines(path))
        {
            var trimmed = line.Trim();
            if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith(";") || trimmed.StartsWith("#") || trimmed.StartsWith("["))
                continue;
            var idx = trimmed.IndexOf('=');
            if (idx > 0)
            {
                var key = trimmed.Substring(0, idx).Trim();
                var value = trimmed.Substring(idx + 1).Trim();
                dict[key] = value;
            }
        }
        return dict;
    }

    static async Task<List<Device>> GetDevicesFromApi(string url, string apiKey, string apiSecret, string clientCode)
    {
        using var client = new HttpClient();
        client.DefaultRequestHeaders.Add("X-API-KEY", apiKey);
        client.DefaultRequestHeaders.Add("X-API-SECRET", apiSecret);
        var response = await client.GetAsync($"{url}?client_code={clientCode}");
        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync();
        var devices = JsonSerializer.Deserialize<List<Device>>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        return devices ?? new List<Device>();
    }

    static string GetSnmpValue(string ip, string oid)
    {
        try
        {
            SimpleSnmp snmp = new SimpleSnmp(ip, "public");
            if (!snmp.Valid)
                return "SNMP inválido";
            var result = snmp.Get(SnmpVersion.Ver2, new string[] { oid });
            if (result == null)
                return "Sem resposta";
            foreach (var entry in result)
            {
                return entry.Value.ToString();
            }
            return "Sem dados";
        }
        catch (Exception ex)
        {
            Log.Error(ex, $"Exceção SNMP [{ip} - {oid}]");
            return $"Erro SNMP: {ex.Message}";
        }
    }

    static async Task<object?> SendDataToApi(Dictionary<string, string> config, List<object> data)
    {
        var url = config["service_url"] + "/report";
        using var client = new HttpClient();
        client.DefaultRequestHeaders.Add("X-API-KEY", config["api_key"]);
        client.DefaultRequestHeaders.Add("X-API-SECRET", config["api_secret"]);
        var payload = new
        {
            client_code = config["client_code"],
            data = data
        };
        var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
        try
        {
            var response = await client.PostAsync(url, content);
            response.EnsureSuccessStatusCode();
            Log.Information($"Dados enviados com sucesso para {url}");
            return await response.Content.ReadAsStringAsync();
        }
        catch (Exception e)
        {
            Log.Error(e, $"Erro ao enviar dados para a API: {e.Message}");
            Console.WriteLine($"Erro ao enviar dados para a API: {e.Message}");
            return null;
        }
    }

    class Device
    {
        public string nome_de_dispositivo { get; set; }
        public string ip_address { get; set; }
        public List<Parameter> parameter { get; set; }
    }
    class Parameter
    {
        public string parameter { get; set; }
        public string mib { get; set; }
    }
}
