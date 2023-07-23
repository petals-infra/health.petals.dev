$(() => {
  $(".show-full-peer-id").click(event => {
    $(".show-full-peer-id").text($(".show-full-peer-id").first().text() == "»" ? "«" : "»");
    $(".short-peer-id, .peer-id").toggle();
    event.preventDefault();
  });
  $(".toggle-rps-details").click(event => {
    $(".toggle-rps-details").text($(".toggle-rps-details").first().text() == "»" ? "«" : "»");
    $(".rps-details").toggle();
    event.preventDefault();
  });

  $(".explain-public-name").click(event => {
    alert(
      'You can specify the name displayed here with the `--public_name` argument. ' +
      'Feel free to use your name, a social media account, or a name of your company ' +
      'to get acknowledgements for hosting a server.\n\n' +
      'The name is only displayed if your server is online and hosts more than 10 blocks. ' +
      'Long names are truncated to 20 characters. ' +
      'If the name starts with "http://" or "https://", we\'ll make it a hyperlink ' +
      '(the address is not truncated).\n\n' +
      'We will ban servers that use offensive names or add links to ' +
      'any offsensive or illegal content.'
    );
    event.preventDefault();
  });
  $(".explain-compute-rps").click(event => {
    alert(
      'Compute throughput, measured in tokens/sec per block. ' +
      'Used for routing requests and load balancing servers between blocks.'
    );
    event.preventDefault();
  });
  $(".explain-network-rps").click(event => {
    alert(
      'Network throughput, measured in tokens/sec. ' +
      'Used for routing requests and load balancing servers between blocks.'
    );
    event.preventDefault();
  });
  $(".explain-precision").click(event => {
    alert(
      'This column shows torch data type used for computation and ' +
      'quantization mode used for storing compressed weights.'
    );
    event.preventDefault();
  });
  $(".explain-adapters").click(event => {
    alert(
      'This column shows LoRA adapters pre-loaded by the server. ' +
      'A client may use one of these adapters if it wants to.\n\n' +
      'To add adapters to your server, pass `--adapters repo_name` argument. ' +
      'To use them in a client, set `AutoDistributedModel.from_pretrained(..., active_adapter="repo_name")` ' +
      'when you create a distributed model.'
    );
    event.preventDefault();
  });
  $(".explain-cache").click(event => {
    alert(
      'This column shows the number of available attention cache tokens (per block). ' +
      'If it is low, inference requests may be delayed or rejected.'
    );
    event.preventDefault();
  });
  $(".explain-avl").click(event => {
    alert(
      'This column shows whether a server is reachable directly or ' +
      'we need to use libp2p relays to traverse NAT/firewalls and reach it. ' +
      'Servers available through relays are usually slower, ' +
      'so we don\'t store DHT keys on them.'
    );
    event.preventDefault();
  });
  $(".explain-pings").click(event => {
    alert(
      'Press show to see round trip times (pings) from this server to next ones ' +
      'in a potential chain. This is used to find the fastest chain for inference.'
    );
    event.preventDefault();
  });

  $('.ping .show').click(function (e) {
    e.preventDefault();

    $('.ping .show').hide();
    $(this).siblings('.hide').show();
    $(`.ping .rtt[data-source-id=${$(this).parent().data("peer-id")}]`).show();
  });
  $('.ping .hide').click(function (e) {
    e.preventDefault();

    $('.ping .hide, .ping .rtt').hide();
    $('.ping .show').show();
  });
});