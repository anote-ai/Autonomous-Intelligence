const API_ENDPOINT = process.env.REACT_APP_BACK_END_HOST;

export function defaultHeaders() {
  const accessToken = localStorage.getItem("accessToken");
  const sessionToken = localStorage.getItem("sessionToken");

  if (accessToken) {
    return {
      Authorization: `Bearer ${accessToken}`,
    };
  } else {
    return {
      Authorization: `Bearer ${sessionToken}`,
    };
  }
}


function updateOptions(options) {
  const update = { ...options };
  const headers = defaultHeaders();
  update.headers = {
    ...headers,
    ...update.headers,
  };
  update.credentials = "include";
  return update;
}

export function refreshAccessToken() {
  return fetch(API_ENDPOINT + "/refresh", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("refreshToken")}`,
    },
  }).then((response) => {
    if (!response.ok) {
      // Return a rejected promise if the response is not successful
      throw new Error;
    }
    return response.json();
  }).then((data) => {
    localStorage.setItem("accessToken", data.accessToken);
    return Promise.resolve({ok: true});
  }).catch((error) => {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    window.location.replace("/");
    return Promise.reject(error);
  });
}

function fetcher(url, options = {}, retryCount = 0) {
  // Hardcode the maximum number of retries
  const maxRetries = 1;

  console.log("updateOptions(options)");
  console.log(updateOptions(options));

  return fetch(API_ENDPOINT + "/" + url, updateOptions(options)).then((response) => {
    if (!response.ok) {
      // Return a rejected promise if the response is not successful
      throw new Error;
    }
    return response;
  }).catch(
    (error) => {
      if (retryCount <= maxRetries) {
        return refreshAccessToken().then((response) => {
          if (!response.ok) {
            // Return a rejected promise if the response is not successful
            throw new Error;
          }
          return fetcher(url, options, retryCount + 1);
        }).catch(
          (error) => {
            return Promise.reject(error);
          }
        );
      } else {
        return Promise.reject(error);
      }
    }
  );
}

export default fetcher;