import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { login, setToken } from "../api";

export function AdminLoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const token = await login(username, password);
      setToken(token);
      navigate("/admin");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось войти.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-shell">
      <section className="login-card">
        <span className="eyebrow">History AI Admin</span>
        <h1>Генератор уроков истории</h1>
        <p>
          Учитель создаёт тему, получает готовую страницу урока с тестом, редактирует и
          публикует ссылку для учеников.
        </p>

        <form onSubmit={handleSubmit} className="login-form">
          <label>
            Логин
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>

          <label>
            Пароль
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>

          {error ? <div className="form-error">{error}</div> : null}

          <button type="submit" className="primary-button" disabled={loading}>
            {loading ? "Входим..." : "Войти в админку"}
          </button>
        </form>
      </section>
    </main>
  );
}

