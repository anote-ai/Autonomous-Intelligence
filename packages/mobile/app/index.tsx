import { Redirect } from "expo-router";
import { useAppAuth } from "./_layout";

export default function Index() {
  const { token } = useAppAuth();
  return token ? <Redirect href="/chat" /> : <Redirect href="/login" />;
}
