 const message = body.message;
    const chatId = BigInt(message.chat.id);
    console.log(`Received message from ${message.from?.id} in chat ${chatId}:`, message.text);

    // Handle new chat member event (bot joining a group)
    if (message.new_chat_member) {
      const newMember = message.new_chat_member;
      
      // Check if new member is bot itself
      if (newMember.is_bot) {
        // Save group information when bot joins
        const group = await getOrCreateGroup({
          id: chatId,
          title: message.chat.title,
          username: message.chat.username,
          type: message.chat.type,
          description: message.chat.description,
        });

        console.log(`Bot joined group: ${group.name} (${chatId})`);
        
        // Send welcome message to the group
        await sendMessageToChat(
          Number(chatId),
          `👋 <b>Halo!</b>\n\nSaya siap mencatat keuangan grup ini.\n\nGunakan format:\n<code>/catat Title | Item1=Harga | Item2=Harga</code>\n\nContoh:\n<code>/catat Makan Siang | Nasi=15000 | Teh=5000</code>`
        );
        
        return NextResponse.json({ 
          ok: true, 
          message: "Group saved successfully" 
        });
      }
      
      // Handle other new members if needed
      return NextResponse.json({ ok: true });
    }
