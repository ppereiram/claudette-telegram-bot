using NetMQ;
using NetMQ.Sockets;
using Newtonsoft.Json; // Recomendado para manejar JSON en NT8

// Dentro de tu clase de Estrategia
private RequestSocket client;

protected override void OnStateChange()
{
    if (State == State.DataLoaded)
    {
        // Inicializar el cliente ZMQ
        AsyncIO.ForceDotNet.Force();
        client = new RequestSocket();
        client.Connect("tcp://localhost:5555");
    }
    else if (State == State.Terminated)
    {
        // Limpiar recursos para que NT8 no se congele
        if (client != null)
        {
            client.Dispose();
            NetMQConfig.Cleanup();
        }
    }
}

protected override void OnBarUpdate()
{
    if (CurrentBar < 20) return;

    // 1. Preparar datos para enviar a Python (ej. últimos 20 cierres)
    List<double> precios = new List<double>();
    for (int i = 19; i >= 0; i--) precios.Add(Close[i]);
    
    string jsonRequest = JsonConvert.SerializeObject(precios);

    // 2. Enviar a Python (Request)
    client.SendFrame(jsonRequest);

    // 3. Recibir la señal de Python (Reply)
    // NOTA AVANZADA: En un bot real, esto debería ir en un hilo (Thread) separado 
    // para no bloquear el hilo principal de la interfaz de NT8 si Python tarda en responder.
    string jsonResponse = client.ReceiveFrameString();
    
    // 4. Decodificar señal y ejecutar
    dynamic respuesta = JsonConvert.DeserializeObject(jsonResponse);
    int señal = respuesta.signal;
    int contratos = respuesta.position_size;

    if (señal == 1)
        EnterLong(contratos, "Compra_Quant");
    else if (señal == -1)
        EnterShort(contratos, "Venta_Quant");
}