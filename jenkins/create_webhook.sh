#!/bin/bash
jenkins_url="http://127.0.0.1:8080"
authorization="c29ubmQ0OjExNWJhNzcyNjg0OGU5ZTJmZWYzZGU5MzdmODJkZDU2Mzg="
consumer_name="${SERVICE_NAME}"
curl "${PACT_BROKER_URL}/groups/${consumer_name}.csv" > consumer.csv
providers=
while IFS=, read -r id name field3 field4 field5 index provider_ids
do
    if [ "$name" = "$consumer_name" ]
    then
        providers="$provider_ids"
    fi
done < consumer.csv
echo "${providers}"
while IFS=, read -r id name field3
do
    providers=$(echo "${providers}" | sed "s/$id/$name/")
done < consumer.csv
echo "${providers}"

provider_names=($(echo "$providers" | tr ',' "\n"))

generate_post_data()
{
  consumerVersionTags='${pactbroker.consumerVersionTags}'
  consumerName='${pactbroker.consumerVersionTags}'
  cat <<EOF
	{
    "consumer": {
      "name": "${consumer_name}"
    },
    "provider": {
      "name": "${provider_name}"
    },
    "request": {
      "method": "POST",
      "url": "${jenkins_url}/job/${provider_name}-run-contract-tests/buildWithParameters?pactConsumerTags=${consumerVersionTags}&pactConsumerName=${consumerName}",
      "headers": {
        "Accept": "application/json",
        "Authorization": "Basic $authorization"
      }
    },
    "events": [
      {
        "name": "contract_content_changed"
      }
    ]
  }
EOF
}

for provider_name in "${provider_names[@]}"
do
  webhook_status=$(curl "${PACT_BROKER_URL}/pacts/provider/${provider_name}/consumer/${consumer_name}/webhooks")
  #echo "${webhook_status}"
  if [[ "$webhook_status" == *"A webhook for the pact between ${consumer_name} and ${provider_name}"* ]]; then
    echo "Webhook already exists!"
  else
    body=$(generate_post_data)
        curl "${PACT_BROKER_URL}/webhooks/provider/${provider_name}/consumer/${consumer_name}" \
    	  -H 'Accept: application/hal+json, application/json, */*; q=0.01' \
    	  -H 'Content-Type: application/json' \
    	  -H 'X-Interface: HAL Browser' \
    	  --data-raw $"${body}" \
      --compressed
  fi
done
