# Kalman update en cada barra
def kalman_update(price, x_prev, P_prev, dt=1, Q=1e-5, R=1e-2):
    F = np.array([[1, dt], [0, 1]])
    H = np.array([[1, 0]])
    x_pred = F @ x_prev
    P_pred = F @ P_prev @ F.T + Q * np.eye(2)
    K = P_pred @ H.T @ np.linalg.inv(H @ P_pred @ H.T + R)
    x_new = x_pred + K * (price - H @ x_pred)
    P_new = (np.eye(2) - K @ H) @ P_pred
    return x_new, P_new, x_new[1]  # velocity como signal