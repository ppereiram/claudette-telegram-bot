using System;
using System.Collections.Generic;
using System.Collections.Concurrent; // Crucial para la cola segura
using System.Threading;
using System.Threading.Tasks; // Crucial para el asincronismo
using NetMQ;
using NetMQ.Sockets;
using Newtonsoft.Json;

public class QuantStrategyAsync : Strategy
{
    // Variables para ZeroMQ y Asincronismo
    private RequestSocket client;
    private Task listenerTask;
    private CancellationTokenSource cancellationTokenSource;
    
    // Nuestro "Buzón de entrada" seguro entre hilos
    private ConcurrentQueue<SignalData> signalQueue;

    // Estructura simple para almacenar la respuesta de Python
    public struct SignalData
    {
        public int Signal;
        public int PositionSize;
    }

    protected override void OnStateChange()
    {
        if (State == State.DataLoaded)
        {
            // 1. Inicializar recursos
            AsyncIO.ForceDotNet.Force();
            client = new RequestSocket();
            client.Connect("tcp://localhost:5555");
            
            signalQueue = new ConcurrentQueue<SignalData>();
            cancellationTokenSource = new CancellationTokenSource();

            // 2. Iniciar el hilo secundario (Listener) en el fondo
            listenerTask = Task.Run(() => ListenToPython(cancellationTokenSource.Token));
        }
        else if (State == State.Terminated)
        {
            // 3. Limpieza vital: Si no detienes el hilo, NT8 colapsará al cerrar
            if (cancellationTokenSource != null)
            {
                cancellationTokenSource.Cancel(); // Avisar al hilo que se detenga
                listenerTask.Wait(1000); // Esperar máximo 1 segundo a que cierre
                cancellationTokenSource.Dispose();
            }
            if (client != null)
            {
                client.Dispose();
                NetMQConfig.Cleanup();
            }
        }
    }

    // Este es el Hilo Secundario (Corre independiente de NT8)
    private void ListenToPython(CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                // Intentar recibir mensaje con un timeout para que no se quede bloqueado eternamente
                string jsonResponse;
                if (client.TryReceiveFrameString(TimeSpan.FromMilliseconds(100), out jsonResponse))
                {
                    // Si Python envió algo, lo decodificamos
                    dynamic respuesta = JsonConvert.DeserializeObject(jsonResponse);
                    
                    SignalData nuevaSeñal = new SignalData 
                    { 
                        Signal = respuesta.signal, 
                        PositionSize = respuesta.position_size 
                    };

                    // Guardamos la orden en la cola para que NT8 la ejecute
                    signalQueue.Enqueue(nuevaSeñal);
                }
            }
            catch (Exception ex)
            {
                // Manejar errores de conexión silenciosamente en el fondo
                Print("Error en ZMQ: " + ex.Message);
            }
        }
    }

    // Este es el Hilo Principal (El corazón de NT8)
    protected override void OnBarUpdate()
    {
        if (CurrentBar < 20) return;

        // --- PARTE 1: ENVIAR DATOS A PYTHON (No bloqueante) ---
        // Extraer los últimos 20 precios
        List<double> precios = new List<double>();
        for (int i = 19; i >= 0; i--) precios.Add(Close[i]);
        
        string jsonRequest = JsonConvert.SerializeObject(precios);
        client.SendFrame(jsonRequest); // Se envía y NT8 sigue su camino


        // --- PARTE 2: REVISAR EL BUZÓN DE ENTRADA Y EJECUTAR ---
        // Revisamos si el hilo secundario metió alguna orden de la IA en la cola
        SignalData ordenPendiente;
        if (signalQueue.TryDequeue(out ordenPendiente))
        {
            // ¡Tenemos una orden de Python! Ahora podemos ejecutarla con seguridad
            // porque OnBarUpdate corre en el hilo principal que permite lanzar órdenes.
            
            if (ordenPendiente.Signal == 1)
            {
                EnterLong(ordenPendiente.PositionSize, "IA_Long");
            }
            else if (ordenPendiente.Signal == -1)
            {
                EnterShort(ordenPendiente.PositionSize, "IA_Short");
            }
        }
    }
}