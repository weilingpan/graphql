# docker run -d --name redis -p 6379:6379 redis #TODO docker compose

port=9000
echo "Service is running on Port: $port"

env_file="dockerenv/test.env"
echo "Loal env file: $env_file"

container_name=local_graphql
image_name=mygraphql:0.0.8
os=

if [[ "$(uname -s)" == "Linux" ]]; then
    os=Linux
    echo "This is $os."
elif [[ "$(uname -s)" == *"MINGW"* || "$(uname -s)" == *"MSYS"* ]]; then
    os=Windows
    echo "This is $od."
else
    echo "Unknown OS."
    exit 1
fi

docker stop $container_name && docker rm $container_name || true

if ! docker image inspect $image_name >/dev/null 2>&1; then
  echo "Image $image_name not found. Building the image..."
  docker build -t $image_name .
fi

run_cmd="docker run"
while IFS= read -r line; do
    run_cmd+=" --env $line"
done < "$env_file"

run_cmd="$run_cmd \
    -it --rm -p $port:9000 \
    -m 2g \
    --cpus=\"2\" \
    --entrypoint bash \
    -v `pwd`/src:/app \
    --name $container_name $image_name"

echo "Creating and exec container $container_name..."
echo "CLI: $run_cmd"
eval $run_cmd

