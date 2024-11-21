port=9000
echo "Service is running on Port: $port"

env_file="dockerenv/test.env"
echo "Loal env file: $env_file"

container_name=local_graphql
image_name=mygraphql

docker stop $container_name && docker rm $container_name || true

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

