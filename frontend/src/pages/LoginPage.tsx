import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

import { Button, Input, Label } from "../components/ui";
import { useAuth } from "../lib/auth";
import type { LoginRequest } from "../types";

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginRequest>();

  async function onSubmit(values: LoginRequest) {
    setError(null);
    try {
      await login(values);
      navigate("/");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4 rounded-lg border border-slate-200 bg-white p-6"
      >
        <h1 className="text-lg font-semibold text-slate-900">Sign in</h1>
        <div>
          <Label>Email</Label>
          <Input
            type="email"
            placeholder="agent@example.com"
            {...register("email", { required: "Email is required" })}
          />
          {errors.email && (
            <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
          )}
        </div>
        <div>
          <Label>Password</Label>
          <Input
            type="password"
            {...register("password", { required: "Password is required" })}
          />
          {errors.password && (
            <p className="mt-1 text-xs text-red-600">{errors.password.message}</p>
          )}
        </div>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
        </Button>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </form>
    </div>
  );
}
